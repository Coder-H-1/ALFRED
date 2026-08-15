import fs from 'fs';
import path from 'path';

export async function POST(req) {
  try {
    const body = await req.json();
    const errorMessage = body.message;
    if (!errorMessage) {
      return new Response(JSON.stringify({ error: 'No message provided' }), { status: 400 });
    }
    const configPath = path.join(process.cwd(), '..', 'Data', 'config.json');
    if (fs.existsSync(configPath)) {
        const data = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        data.errors = {
            visible: true,
            text: errorMessage,
            zone: "update"
        };
        fs.writeFileSync(configPath, JSON.stringify(data, null, 4));
    }
    return new Response(JSON.stringify({ success: true }), { status: 200 });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  }
}
