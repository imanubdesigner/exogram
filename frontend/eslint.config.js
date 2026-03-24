import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import pluginSecurity from 'eslint-plugin-security'

// Browser globals explícitos (equivalente a env: { browser: true } en eslintrc)
const browserGlobals = {
  window: 'readonly',
  document: 'readonly',
  navigator: 'readonly',
  location: 'readonly',
  history: 'readonly',
  sessionStorage: 'readonly',
  localStorage: 'readonly',
  fetch: 'readonly',
  console: 'readonly',
  URL: 'readonly',
  Blob: 'readonly',
  FormData: 'readonly',
  FileReader: 'readonly',
  AbortController: 'readonly',
  setTimeout: 'readonly',
  clearTimeout: 'readonly',
  setInterval: 'readonly',
  clearInterval: 'readonly',
  Event: 'readonly',
  HTMLElement: 'readonly',
  crypto: 'readonly',
  alert: 'readonly',
  confirm: 'readonly',
  prompt: 'readonly',
  URLSearchParams: 'readonly',
}

export default [
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  pluginSecurity.configs.recommended,
  {
    files: ['src/**/*.{js,vue}'],
    languageOptions: {
      globals: browserGlobals,
    },
    rules: {
      // Permitir console.warn/error; silenciar console.log
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      // Advertir variables sin usar, no bloquear CI
      'no-unused-vars': 'warn',

      // Vue — componentes de una sola palabra son válidos en este proyecto
      'vue/multi-word-component-names': 'off',
      // Vue — reglas de formato cosmético: demasiado estrictas para una codebase existente
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/multiline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/attributes-order': 'off',

      // Security — detect-object-injection tiene alta tasa de falsos positivos
      // en acceso con bracket notation estándar (obj[key])
      'security/detect-object-injection': 'off',

      // Vue — indentación cosmética, no bloquear CI en codebase existente
      'vue/html-indent': 'off',
      // Vue — side effects en computed son un smell pero no rompen en producción;
      // advertir sin bloquear hasta que se refactorice
      'vue/no-side-effects-in-computed-properties': 'warn',

      // JS — escapes innecesarios y variables no usadas: advertir, no bloquear
      'no-useless-escape': 'warn',
    },
  },
  {
    ignores: ['dist/', 'node_modules/', '**/*.test.js'],
  },
]
