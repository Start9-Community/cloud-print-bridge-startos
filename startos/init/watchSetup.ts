import { configure } from '../actions/configure'
import { configJson, isComplete } from '../fileModels/config.json'
import { i18n } from '../i18n'
import { sdk } from '../sdk'

// A reactive read, so emptying a required field re-raises the prompt. StartOS
// clears an unconditional task itself once its action runs.
export const watchSetup = sdk.setupOnInit(async (effects) => {
  if (isComplete(await configJson.read().const(effects))) return

  await sdk.action.createOwnTask(effects, configure, 'critical', {
    reason: i18n('Set your Nextcloud account and printer to start printing'),
  })
})
