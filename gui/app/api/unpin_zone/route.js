import fs from 'fs';
import path from 'path';

export async function POST(req) {
  try {
    const body = await req.json();
    const zoneName = body.zone;
    
    const layoutPath = path.join(process.cwd(), '..', 'Data', 'layout_state.json');
    if (fs.existsSync(layoutPath)) {
        const layout = JSON.parse(fs.readFileSync(layoutPath, 'utf8'));
        
        let changed = false;
        // Unpin anything in this zone that is pinned
        for (const boxName in layout) {
            if (layout[boxName].zone === zoneName && layout[boxName].pinned) {
                layout[boxName].pinned = false;
                changed = true;
            }
        }
        
        if (changed) {
            fs.writeFileSync(layoutPath, JSON.stringify(layout, null, 4));
        }
    }
    return new Response(JSON.stringify({ success: true }), { status: 200 });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  }
}
