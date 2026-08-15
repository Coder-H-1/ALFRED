import fs from 'fs';
import path from 'path';

export async function POST(req) {
  try {
    const body = await req.json();
    const command = body.command;
    if (!command) {
      return new Response(JSON.stringify({ error: 'No command provided' }), { status: 400 });
    }
    const dataPath = path.join(process.cwd(), '..', 'Data', 'command.txt');
    fs.writeFileSync(dataPath, command);
    return new Response(JSON.stringify({ success: true }), { status: 200 });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  }
}
