import { NextResponse } from "next/server";
import type { User } from "../../../models/user";

const users: User[] = [];

export async function GET() {
  return NextResponse.json(users);
}

export async function POST(request: Request) {
  const body = await request.json();
  const user: User = { id: users.length + 1, name: body.name };
  users.push(user);
  return NextResponse.json(user, { status: 201 });
}
