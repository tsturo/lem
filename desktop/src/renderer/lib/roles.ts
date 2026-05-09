export interface RoleMeta {
  icon: string
  tone: string
  label: string
}

export const ROLE_META: Record<string, RoleMeta> = {
  architect: { icon: '🏗', tone: 'purple', label: 'Architect' },
  designer: { icon: '🎨', tone: 'teal', label: 'Designer' },
  market: { icon: '📈', tone: 'navy', label: 'Market' },
  'jtbd-extractor': { icon: '🎯', tone: 'amber', label: 'JTBD' },
  'frame-shifter': { icon: '🔭', tone: 'indigo', label: 'Reframer' },
  'disagreement-detector': { icon: '⚡', tone: 'orange', label: 'Detector' },
  'branch-skeptic': { icon: '🔍', tone: 'red', label: 'Skeptic' },
  pruner: { icon: '✂️', tone: 'rose', label: 'Pruner' },
  distiller: { icon: '⚗️', tone: 'cyan', label: 'Distiller' },
  'cross-skeptic': { icon: '❌', tone: 'red', label: 'Cross-Skeptic' },
  'kill-case-skeptic': { icon: '💀', tone: 'gray', label: 'Kill-Case' },
  synthesizer: { icon: '✨', tone: 'green', label: 'Synthesizer' },
}
