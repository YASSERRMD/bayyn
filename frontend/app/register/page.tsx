"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth-context";

const schema = z.object({
  name: z.string().max(255).optional(),
  email: z.string().email("Enter a valid email"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(128, "Password is too long"),
});

type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setServerError(null);
    try {
      await registerUser(data.email, data.password, data.name || undefined);
      router.push("/history");
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    }
  };

  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-bayyn-navy mb-2">Create account</h1>
        <p className="text-sm text-gray-500 mb-6">
          Save your transcripts across sessions.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Input
              {...register("name")}
              type="text"
              placeholder="Name (optional)"
              autoFocus
              disabled={isSubmitting}
              className="h-11"
            />
          </div>

          <div>
            <Input
              {...register("email")}
              type="email"
              placeholder="Email"
              disabled={isSubmitting}
              className="h-11"
            />
            {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
          </div>

          <div>
            <Input
              {...register("password")}
              type="password"
              placeholder="Password (min 8 chars)"
              disabled={isSubmitting}
              className="h-11"
            />
            {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
          </div>

          {serverError && <p className="text-sm text-red-600">{serverError}</p>}

          <Button type="submit" disabled={isSubmitting} className="w-full h-11">
            {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create account"}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-500">
          Already have an account?{" "}
          <Link href="/login" className="text-bayyn-navy font-medium hover:underline">
            Sign in
          </Link>
        </p>

        <p className="mt-6 text-center text-xs text-gray-400">
          Bayyn never stores your video or audio — only the transcript text.
        </p>
      </div>
    </div>
  );
}
