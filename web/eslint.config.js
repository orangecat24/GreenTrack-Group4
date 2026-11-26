import js from '@eslint/js'
import globals from 'globals'
import hooks from 'eslint-plugin-react-hooks'
import refresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  {
    // Python environments contain third-party JavaScript (for example in pip).
    // Exclude them even if one was accidentally created inside web/; lint is
    // meant to check our source, not installed dependency internals.
    ignores: ['**/.venv/**', '**/venv/**', 'dist/**', 'coverage/**',
      'playwright-report/**', 'test-results/**', '*.tsbuildinfo'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['scripts/**/*.mjs'],
    languageOptions: { globals: globals.node },
  },
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    plugins: { 'react-hooks': hooks, 'react-refresh': refresh },
    rules: {
      // Enforce hook correctness and effect dependencies without introducing
      // React Compiler-specific optimization rules into this introductory SPA.
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'error',
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  },
)
