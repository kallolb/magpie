const colors = [
  'bg-red-100 text-red-800',
  'bg-blue-100 text-blue-800',
  'bg-green-100 text-green-800',
  'bg-yellow-100 text-yellow-800',
  'bg-purple-100 text-purple-800',
  'bg-pink-100 text-pink-800',
  'bg-indigo-100 text-indigo-800',
  'bg-cyan-100 text-cyan-800',
]

export function getTagColor(tagName: string): string {
  const hash = tagName
    .split('')
    .reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return colors[hash % colors.length]
}

export function getColorPair(
  name: string
): { bg: string; text: string; border: string } {
  const colorClass = getTagColor(name)
  const [bg, text] = colorClass.split(' ')
  const borderMap: Record<string, string> = {
    'border-red-300': 'bg-red-100',
    'border-blue-300': 'bg-blue-100',
    'border-green-300': 'bg-green-100',
    'border-yellow-300': 'bg-yellow-100',
    'border-purple-300': 'bg-purple-100',
    'border-pink-300': 'bg-pink-100',
    'border-indigo-300': 'bg-indigo-100',
    'border-cyan-300': 'bg-cyan-100',
  }
  const border = Object.keys(borderMap).find((k) => borderMap[k] === bg) || 'border-gray-300'
  return { bg, text, border }
}
