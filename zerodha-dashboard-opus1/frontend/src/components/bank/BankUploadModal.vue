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
          <div v-if="!uploadStatus || uploadStatus === 'failed'" class="upload-section">
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
            <button class="retry-btn" @click="resetUpload">Try Again</button>
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
            v-if="!uploadStatus || uploadStatus === 'failed'"
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
  } catch (error) {
    // Error is already handled in store
    console.error('Upload failed:', error)
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
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 16px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #111827;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  color: #6b7280;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s;
}

.close-btn:hover:not(:disabled) {
  background: #f3f4f6;
  color: #111827;
}

.close-btn:disabled {
  opacity: 0.5;
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
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafafa;
}

.drop-zone:hover {
  border-color: #667eea;
  background: #f9fafb;
}

.drop-zone.drag-over {
  border-color: #667eea;
  background: #eef2ff;
}

.drop-zone.has-file {
  border-color: #10b981;
  background: #f0fdf4;
  padding: 20px;
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.upload-icon {
  font-size: 48px;
  opacity: 0.6;
}

.drop-text {
  margin: 0;
  color: #374151;
  font-size: 14px;
}

.drop-text strong {
  color: #667eea;
  font-weight: 600;
}

.file-hint {
  margin: 0;
  color: #6b7280;
  font-size: 12px;
}

.file-selected {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.file-icon {
  width: 48px;
  height: 48px;
  background: #10b981;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  text-align: left;
}

.file-name {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  word-break: break-word;
}

.file-size {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
}

.remove-file-btn {
  width: 32px;
  height: 32px;
  background: #fee2e2;
  color: #dc2626;
  border: none;
  border-radius: 50%;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.remove-file-btn:hover {
  background: #fecaca;
}

.error-message {
  width: 100%;
  padding: 12px;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 14px;
  text-align: center;
}

.progress-section {
  padding: 20px 0;
}

.progress-icon {
  margin-bottom: 16px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e5e7eb;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-info {
  width: 100%;
}

.progress-status {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  text-align: center;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-percent {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
  text-align: center;
}

.error-section {
  padding: 20px 0;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.error-text {
  margin: 0 0 16px 0;
  color: #dc2626;
  font-size: 14px;
  text-align: center;
}

.retry-btn {
  padding: 10px 24px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-btn:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px 24px;
  border-top: 1px solid #e5e7eb;
}

.btn-secondary,
.btn-primary {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.5;
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
