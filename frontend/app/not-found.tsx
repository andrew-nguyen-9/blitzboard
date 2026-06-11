import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-32 text-center">
      <div className="font-display text-display-lg text-accent">404</div>
      <p className="mt-4 text-body-lg text-ink-muted">That play didn&apos;t connect.</p>
      <Link href="/" className="mt-8 inline-block rounded-full bg-accent px-5 py-2.5 font-semibold text-bg">
        Back to the war room
      </Link>
    </div>
  );
}
