import { cp, rm, stat } from 'node:fs/promises'
import { join } from 'node:path'

async function exists(p) {
  try { await stat(p); return true } catch { return false }
}

async function main() {
  const src = join(process.cwd(), 'data')
  const dst = join(process.cwd(), 'public', 'data')
  if (!(await exists(src))) {
    console.warn('[prepare:public] no data/ directory to copy')
    return
  }
  if (await exists(dst)) {
    await rm(dst, { recursive: true, force: true })
  }
  await cp(src, dst, { recursive: true })
  console.log(`[prepare:public] copied data -> public/data`)
}

main().catch(err => { console.error(err); process.exit(1) })

