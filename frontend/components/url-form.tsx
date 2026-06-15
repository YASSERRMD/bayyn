"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { Loader2, Link as LinkIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

const schema = z.object({
  url: z
    .string()
    .min(10, "Please enter a valid URL")
    .url("Please enter a valid URL")
    .refine(
      (val) => val.startsWith("http://") || val.startsWith("https://"),
      "URL must start with http:// or https://"
    ),
});

type FormData = z.infer<typeof schema>;

export function UrlForm() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setServerError(null);
    try {
      const result = await api.createJob(data.url);
      router.push(`/transcriptions/${result.job_id}`);
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="w-full space-y-3">
      <div className="flex gap-3">
        <div className="relative flex-1">
          <LinkIcon
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5"
            aria-hidden="true"
          />
          <Input
            {...register("url")}
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            className="pl-11 h-14 text-base rounded-xl border-gray-200 focus:border-bayyn-gold"
            disabled={isSubmitting}
            autoFocus
          />
        </div>
        <Button
          type="submit"
          disabled={isSubmitting}
          size="lg"
          className="h-14 px-8 rounded-xl text-base"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Processing…
            </>
          ) : (
            "Get Transcript"
          )}
        </Button>
      </div>

      {errors.url && (
        <p className="text-sm text-red-600">{errors.url.message}</p>
      )}
      {serverError && (
        <p className="text-sm text-red-600">{serverError}</p>
      )}
    </form>
  );
}
