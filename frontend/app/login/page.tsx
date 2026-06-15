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
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setServerError(null);
    try {
      await login(data.email, data.password);
      router.push("/history");
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Login failed. Please try again.");
    }
  };

  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-bayyn-navy mb-2">Sign in</h1>
        <p className="text-sm text-gray-500 mb-6">
          Access your transcript history.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Input
              {...register("email")}
              type="email"
              placeholder="Email"
              autoFocus
              disabled={isSubmitting}
              className="h-11"
            />
            {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
          </div>

          <div>
            <Input
              {...register("password")}
              type="password"
              placeholder="Password"
              disabled={isSubmitting}
              className="h-11"
            />
            {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
          </div>

          {serverError && <p className="text-sm text-red-600">{serverError}</p>}

          <Button type="submit" disabled={isSubmitting} className="w-full h-11">
            {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Sign in"}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-500">
          No account?{" "}
          <Link href="/register" className="text-bayyn-navy font-medium hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
