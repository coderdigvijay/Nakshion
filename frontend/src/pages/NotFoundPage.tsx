import { SearchX } from "lucide-react";
import { AuthLayout } from "../components/auth/AuthLayout";
import { ButtonLink } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";

export default function NotFoundPage() {
  return (
    <AuthLayout>
      <h1 className="sr-only">Page not found</h1>
      <EmptyState
        icon={<SearchX />}
        title="This page isn't in the sky"
        body="The link may be old or mistyped."
        headingLevel="h2"
        action={
          <ButtonLink to="/" variant="primary">
            Go home
          </ButtonLink>
        }
      />
    </AuthLayout>
  );
}
