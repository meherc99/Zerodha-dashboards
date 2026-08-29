<template>
  <Teleport to="body">
    <div v-if="isOpen" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Upload Bank Statement</h2>
          <button class="close-btn" @click="handleClose" :disabled="isProcessing">×</button>
        </div>

        <div class="modal-body">
          <!-- File Upload Section -->
          <div
            v-if="!uploadStatus || (uploadStatus === 'failed' && !statementId)"
            class="upload-section"
          >
            <div
              class="drop-zone"
              :class="{ 'drag-over': isDragging, 'has-file': selectedFile }"
              @drop.prevent="handleDrop"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
              @click="triggerFileInput"
            >
              <input
                ref="fileInput"
                type="file"
                accept=".pdf"
                @change="handleFileSelect"
                style="display: none"
              />

              <div v-if="!selectedFile" class="drop-zone-content">
                <div class="upload-icon">📄</div>
                <p class="drop-text">
                  <strong>Click to upload</strong> or drag and drop
                </p>
                <p class="file-hint">PDF only (max 10MB)</p>
              </div>

              <div v-else class="file-selected">
                <div class="file-icon">✓</div>
                <div class="file-info">
                  <p class="file-name">{{ selectedFile.name }}</p>
                  <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
                </div>
                <button class="remove-file-btn" @click.stop="removeFile">×</button>
              </div>
            </div>

            <div v-if="validationError" class="error-message">
              {{ validationError }}
            </div>
          </div>

          <!-- Progress Section -->
          <div v-if="uploadStatus && uploadStatus !== 'failed'" class="progress-section">
            <div class="progress-icon">
              <div class="spinner"></div>
            </div>

            <div class="progress-info">
              <p class="progress-status">{{ statusMessage }}</p>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: progress + '%' }"></div>
              </div>
              <p class="progress-percent">{{ progress }}%</p>
            </div>
          </div>

          <!-- Error Section -->
          <div v-if="uploadStatus === 'failed' && uploadError" class="error-section">
            <div class="error-icon">⚠️</div>
            <p class="error-text">{{ uploadError }}</p>
            <div class="recovery-actions">
              <button
                v-if="statementId"
                class="retry-btn"
                @click="retryParsing"
              >
                Retry parsing
              </button>
              <button
                v-if="statementId"
                class="discard-btn"
                @click="discardUpload"
              >
                Discard upload
              </button>
              <button v-else class="retry-btn" @click="startOver">
                Try another file
              </button>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button
            class="btn-secondary"
            @click="handleClose"
            :disabled="isProcessing"
          >
            Cancel
          </button>
          <button
            v-if="!uploadStatus || (uploadStatus === 'failed' && !statementId)"
            class="btn-primary"
            @click="handleUpload"
            :disabled="!selectedFile || isProcessing"
          >
            Upload
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useBankAccountsStore } from '@/stores/bankAccounts'
import { storeToRefs } from 'pinia'

const bankAccountsStore = useBankAccountsStore()
const { uploadModal } = storeToRefs(bankAccountsStore)

const fileInput = ref(null)
const selectedFile = ref(null)
const validationError = ref(null)
const isDragging = ref(false)

const isOpen = computed(() => uploadModal.value.isOpen)
const uploadStatus = computed(() => uploadModal.value.status)
const progress = computed(() => uploadModal.value.progress)
const uploadError = computed(() => uploadModal.value.error)
const statementId = computed(() => uploadModal.value.statementId)

const isProcessing = computed(() => {
  return uploadStatus.value === 'uploading' || uploadStatus.value === 'parsing'
})

const statusMessage = computed(() => {
  switch (uploadStatus.value) {
    case 'uploading':
      return 'Uploading statement...'
    case 'parsing':
      return 'Parsing transactions...'
    case 'review':
      return 'Ready for review!'
    default:
      return ''
  }
})

// Watch for modal close to reset state
watch(() => uploadModal.value.isOpen, (newVal) => {
  if (!newVal) {
    resetUpload()
  }
})

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event) => {
  const file = event.target.files?.[0]
  if (file) {
    validateAndSetFile(file)
  }
}

const handleDrop = (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files?.[0]
  if (file) {
    validateAndSetFile(file)
  }
}

const validateAndSetFile = (file) => {
  validationError.value = null

  // Check file type
  if (file.type !== 'application/pdf') {
    validationError.value = 'Only PDF files are allowed'
    return
  }

  // Check file size (10MB = 10 * 1024 * 1024 bytes)
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    validationError.value = 'File size must be less than 10MB'
    return
  }

  selectedFile.value = file
}

const removeFile = () => {
  selectedFile.value = null
  validationError.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const handleUpload = async () => {
  if (!selectedFile.value) return

  try {
    await bankAccountsStore.uploadStatement(
      uploadModal.value.bankAccountId,
      selectedFile.value
    )
  } catch {
    // Error is already handled in store
  }
}

const resetUpload = () => {
  selectedFile.value = null
  validationError.value = null
  isDragging.value = false
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const startOver = () => {
  bankAccountsStore.resetUploadAttempt()
  resetUpload()
}

const retryParsing = async () => {
  try {
    await bankAccountsStore.retryStatementParse()
  } catch {
    // The store retains the uploaded statement and exposes the retry error.
  }
}

const discardUpload = async () => {
  try {
    await bankAccountsStore.discardStatement()
    resetUpload()
  } catch {
    uploadModal.value.error = 'Failed to discard statement'
  }
}

const handleClose = () => {
  if (!isProcessing.value) {
    bankAccountsStore.closeUploadModal()
  }
}

const handleOverlayClick = () => {
  handleClose()
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.72);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md), inset 0 1px 0 rgba(255,255,255,0.05);
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.modal-content::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  background: linear-gradient(90deg, transparent, rgba(61,126,255,0.5), rgba(167,139,250,0.4), transparent);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.02em;
}

.close-btn {
  background: var(--color-surface-strong);
  border: 1px solid var(--color-border-strong);
  font-size: 1.3rem;
  color: var(--color-text-soft);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.18s;
}

.close-btn:hover:not(:disabled) {
  background: var(--color-surface-subtle);
  border-color: var(--color-border-glow);
  color: var(--color-text);
}

.close-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.modal-body {
  padding: 24px;
  min-height: 200px;
}

.upload-section,
.progress-section,
.error-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.drop-zone {
  width: 100%;
  border: 1.5px dashed var(--color-border-strong);
  border-radius: var(--radius-md);
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--color-surface-subtle);
}

.drop-zone:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.drop-zone.drag-over {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  box-shadow: 0 0 24px rgba(61, 126, 255, 0.15);
}

.drop-zone.has-file {
  border-color: rgba(13, 217, 142, 0.4);
  background: var(--color-positive-soft);
  padding: 20px;
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.upload-icon {
  font-size: 40px;
  opacity: 0.55;
}

.drop-text {
  margin: 0;
  color: var(--color-text-soft);
  font-size: 0.875rem;
}

.drop-text strong {
  color: var(--color-primary-dark);
  font-weight: 700;
}

.file-hint {
  margin: 0;
  color: var(--color-text-faint);
  font-size: 0.75rem;
}

.file-selected {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.file-icon {
  width: 44px;
  height: 44px;
  background: var(--color-positive-soft);
  color: var(--color-positive);
  border: 1px solid rgba(13, 217, 142, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: bold;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  text-align: left;
}

.file-name {
  margin: 0 0 4px 0;
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--color-text);
  word-break: break-word;
}

.file-size {
  margin: 0;
  font-size: 0.75rem;
  color: var(--color-text-soft);
}

.remove-file-btn {
  width: 30px;
  height: 30px;
  background: var(--color-negative-soft);
  color: var(--color-negative);
  border: 1px solid rgba(255, 69, 96, 0.3);
  border-radius: 50%;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.18s;
  flex-shrink: 0;
}

.remove-file-btn:hover {
  border-color: var(--color-negative);
  background: rgba(255, 69, 96, 0.2);
}

.error-message {
  width: 100%;
  padding: 12px 14px;
  background: var(--color-negative-soft);
  border: 1px solid rgba(255, 69, 96, 0.28);
  border-left: 3px solid var(--color-negative);
  border-radius: 8px;
  color: var(--color-negative);
  font-size: 0.83rem;
  text-align: center;
}

.progress-section {
  padding: 20px 0;
}

.progress-icon {
  margin-bottom: 16px;
}

.spinner {
  width: 44px;
  height: 44px;
  border: 3px solid var(--color-border-strong);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 900ms linear infinite;
  box-shadow: 0 0 14px rgba(61, 126, 255, 0.3);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-info {
  width: 100%;
}

.progress-status {
  margin: 0 0 12px 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
  text-align: center;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: var(--color-border-strong);
  border-radius: 99px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: var(--gradient-primary);
  transition: width 0.3s ease;
  border-radius: 99px;
  box-shadow: 0 0 10px rgba(61, 126, 255, 0.4);
}

.progress-percent {
  margin: 0;
  font-size: 0.8rem;
  color: var(--color-text-soft);
  text-align: center;
}

.error-section {
  padding: 20px 0;
}

.error-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.error-text {
  margin: 0 0 16px 0;
  color: var(--color-negative);
  font-size: 0.875rem;
  text-align: center;
}

.retry-btn {
  padding: 10px 24px;
  background: linear-gradient(135deg, #3d7eff, #5b6ef5);
  color: #fff;
  border: 1px solid var(--color-primary);
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 0 16px rgba(61, 126, 255, 0.22);
  transition: all 0.18s;
}

.retry-btn:hover {
  background: linear-gradient(135deg, #5090ff, #7280ff);
  box-shadow: 0 0 24px rgba(61, 126, 255, 0.38);
  transform: translateY(-1px);
}

.recovery-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 9px;
}

.discard-btn {
  padding: 10px 18px;
  border: 1px solid rgba(255, 69, 96, 0.3);
  border-radius: 8px;
  background: var(--color-negative-soft);
  color: var(--color-negative);
  font-size: 0.875rem;
  font-weight: 650;
  cursor: pointer;
  transition: border-color 150ms, background 150ms;
}

.discard-btn:hover {
  border-color: var(--color-negative);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px 24px;
  border-top: 1px solid var(--color-border);
}

.btn-secondary,
.btn-primary {
  padding: 10px 24px;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s;
}

.btn-secondary {
  border: 1px solid var(--color-border-strong);
  background: var(--color-surface-strong);
  color: var(--color-text-soft);
}

.btn-secondary:hover:not(:disabled) {
  border-color: var(--color-border-glow);
  color: var(--color-text);
}

.btn-primary {
  border: 1px solid var(--color-primary);
  background: linear-gradient(135deg, #3d7eff, #5b6ef5);
  color: #fff;
  box-shadow: 0 0 16px rgba(61, 126, 255, 0.22);
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #5090ff, #7280ff);
  box-shadow: 0 0 26px rgba(61, 126, 255, 0.38);
  transform: translateY(-1px);
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 640px) {
  .modal-overlay {
    padding: 0;
  }

  .modal-content {
    border-radius: 0;
    max-height: 100vh;
    height: 100vh;
  }

  .drop-zone {
    padding: 30px 15px;
  }
}
</style>
