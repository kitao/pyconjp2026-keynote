import assert from 'node:assert/strict';
import { test } from 'node:test';
import { cloudflare } from '../scripts/cloudflare.js';

test('API credentials stop the command without exposing their values', () => {
  for (const name of ['CLOUDFLARE_API_TOKEN', 'CF_API_TOKEN', 'CLOUDFLARE_API_KEY', 'CF_API_KEY']) {
    const value = 'synthetic-secret-for-test';
    let invoked = false;
    assert.throws(
      () =>
        cloudflare(['deploy'], { [name]: value }, () => {
          invoked = true;
        }),
      (error) => !error.message.includes(value) && /keychain/.test(error.message),
    );
    assert.equal(invoked, false);
  }
});

test('every Cloudflare invocation forces secure storage without plaintext fallback', () => {
  const env = { CLOUDFLARE_AUTH_USE_KEYRING: 'false', PATH: '/example' };
  const status = cloudflare(['deploy', '--dry-run'], env, (command, args, options) => {
    assert.equal(command, process.execPath);
    assert.match(args[0], /wrangler[/\\]bin[/\\]wrangler\.js$/);
    assert.deepEqual(args.slice(1), ['deploy', '--dry-run']);
    assert.equal(options.env.CLOUDFLARE_AUTH_USE_KEYRING, 'true');
    assert.equal(options.env.WRANGLER_SEND_METRICS, 'false');
    assert.equal(options.env.PATH, env.PATH);
    return { status: 7 };
  });
  assert.equal(status, 7);
  assert.equal(env.CLOUDFLARE_AUTH_USE_KEYRING, 'false');
});

test('failure to start or termination cannot report success', () => {
  const failure = new Error('process failed to start');
  assert.throws(
    () => cloudflare(['deploy'], {}, () => ({ error: failure })),
    (error) => error === failure,
  );
  assert.equal(
    cloudflare(['deploy'], {}, () => ({ status: null, signal: 'SIGTERM' })),
    1,
  );
});
