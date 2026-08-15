import { NextResponse } from 'next/server';
export const dynamic = "force-static";
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    const configPath = path.join(process.cwd(), '..', 'Data', 'config.json');
    if (fs.existsSync(configPath)) {
      const fileContents = fs.readFileSync(configPath, 'utf8');
      const data = JSON.parse(fileContents);
      return NextResponse.json(data);
    } else {
      return NextResponse.json({ error: 'Config not found' }, { status: 404 });
    }
  } catch (error) {
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
