import { mergeConfig, defineConfig } from 'vitest/config'
import viteConfig from './vite.config.js'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'node',
      globals: true,
      setupFiles: ['./tests/setup.js'],
      clearMocks: true,
      restoreMocks: true
    }
  })
)
