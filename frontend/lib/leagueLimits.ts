// Shared league limits. Lives outside the "use server" actions file (which may only export async
// functions) so both the server action and the client manager import one source of truth.
export const MAX_LEAGUES = 3;
