import js from '@eslint/js';
import globals from 'globals';
import { defineConfig, globalIgnores } from 'eslint/config';

export default defineConfig([
  // Directories in .gitignore that can hold generated or downloaded JavaScript, and the
  // production tools, kept as they were used for the talk.
  globalIgnores(['dist/', '.keynote-build-*/', '.wrangler/', '.offline/', '.venv/', 'tools/']),
  js.configs.recommended,
  {
    languageOptions: { globals: globals.node },
  },
  {
    // Callbacks passed to page.evaluate() run in the browser.
    files: ['tests/browser/**/*.js'],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
  },
  {
    rules: {
      eqeqeq: 'error',
      'no-var': 'error',
      'prefer-const': 'error',
    },
  },
]);
