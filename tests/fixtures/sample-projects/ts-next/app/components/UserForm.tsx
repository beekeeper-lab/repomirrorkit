"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

type FormValues = { name: string; email?: string };

export function UserForm() {
  const router = useRouter();
  const { register, handleSubmit } = useForm<FormValues>();

  async function onSubmit(values: FormValues) {
    await fetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    router.push("/");
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <label htmlFor="name">Name</label>
      <input id="name" type="text" {...register("name", { required: true, minLength: 2 })} />
      <label>
        Email
        <input type="email" {...register("email")} />
      </label>
      <button type="submit">Save</button>
    </form>
  );
}
