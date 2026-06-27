import { defineConfig } from 'tsdown'

export default defineConfig({
  entry: {
    index: 'src/main.ts',
  },
  format: ['esm'],
  target: 'node22',
  platform: 'node',
  outDir: 'dist',
  clean: true,
})
