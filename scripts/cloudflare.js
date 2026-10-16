import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export function cloudflare(args, env = process.env, spawn = spawnSync) {
  if (
    args.some(
      (arg, index) =>
        arg === '--no-use-keyring' ||
        arg === '--use-keyring=false' ||
        (arg === '--use-keyring' && args[index + 1] === 'false'),
    ) ||
    args.slice(0, 3).join(' ') === 'auth keyring disable'
  ) {
    throw new Error('Disabling OS-keychain-backed authentication is not allowed.');
  }
  if (
    ['CLOUDFLARE_API_TOKEN', 'CF_API_TOKEN', 'CLOUDFLARE_API_KEY', 'CF_API_KEY'].some(
      (name) => env[name],
    )
  ) {
    throw new Error('Use Cloudflare OAuth with the OS keychain. Unset API token/key variables.');
  }
  const wrangler = join(
    dirname(createRequire(import.meta.url).resolve('wrangler/package.json')),
    'bin/wrangler.js',
  );
  const result = spawn(process.execPath, [wrangler, ...args], {
    stdio: 'inherit',
    env: {
      ...env,
      CLOUDFLARE_AUTH_USE_KEYRING: 'true',
      WRANGLER_SEND_METRICS: 'false',
    },
  });
  if (result.error) throw result.error;
  return result.status ?? 1;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    process.exitCode = cloudflare(process.argv.slice(2));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
