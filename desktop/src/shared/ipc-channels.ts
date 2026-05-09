export const IPC = {
  SETTINGS_GET: 'settings:get',
  SETTINGS_SET: 'settings:set',
  CLAUDE_DETECT: 'claude:detect',
  LIBRARY_LIST: 'library:list',
  RUN_START: 'run:start',
  RUN_CANCEL: 'run:cancel',
  RUN_EVENT: 'run:event',
  RUN_LOG: 'run:log',
  WORKSPACE_READ_BRIEF: 'workspace:read-brief',
  SHELL_OPEN_EXTERNAL: 'shell:open-external',
} as const
