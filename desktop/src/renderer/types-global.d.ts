import type { Settings, LibraryItem } from '../shared/types'

declare global {
  interface Window {
    lem: {
      settings: {
        get(): Promise<Settings>
        set(settings: Settings): Promise<void>
      }
      claude: {
        detect(): Promise<string | null>
        pickPath(): Promise<string | null>
        login(claudePath: string): Promise<void>
      }
      shell: {
        openExternal(url: string): Promise<void>
      }
      library: {
        list(): Promise<LibraryItem[]>
      }
    }
  }
}
