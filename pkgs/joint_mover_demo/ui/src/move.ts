import type { AppServices } from "./zara";

/**
 * Sends moves to this app's backend (`joint_mover_node.py`): the `zara_commands` command
 * `move_joint(joint_name: str, position: float)` publishes one MotorMove (position in degrees,
 * fixed 2.5 s move time) to crab_api's `/motor/move` and replies `{"joint": joint_name, "target": position}`.
 * The reply only means the app published the move: crab_api only logs an unknown joint, and the
 * firmware rejects a goal outside the joint's bounds; neither comes back to the caller.
 * The Driver Station sends it through Cortex's `POST /instances/{id}/command`, which older Cortex
 * builds don't have.
 */
export const MOVE_JOINT_COMMAND = "move_joint";

/**
 * Ask this instance to move one joint. Resolves with the app's reply; rejects with a message fit
 * to show.
 */
export async function moveJoint(services: AppServices, jointName: string, position: number): Promise<unknown> {
  if (!jointName.trim()) throw new Error("Enter a joint name.");
  if (!Number.isFinite(position)) throw new Error("Enter a finite position in degrees.");
  try {
    return await services.command(MOVE_JOINT_COMMAND, { joint_name: jointName.trim(), position });
  } catch (error) {
    throw new Error(describeMoveError(error), { cause: error });
  }
}

/**
 * The Driver Station rejects with an `AppRequestError` (lib/app-ui/services.ts) when Cortex or the
 * app answered with an error. The class isn't part of the page contract, so it is recognised by
 * shape. `explained` is false when the response had no JSON error message.
 */
type AppRequestError = Error & { status: number; explained: boolean };

function isAppRequestError(error: unknown): error is AppRequestError {
  return (
    error instanceof Error &&
    error.name === "AppRequestError" &&
    typeof (error as Partial<AppRequestError>).status === "number"
  );
}

function describeMoveError(error: unknown) {
  if (isAppRequestError(error)) {
    // Cortex builds without the command route answer with their catch-all `{"error": "not found"}`
    // (develop) or Go's plain-text "404 page not found". A missing instance ("instance not found")
    // or an unknown command ("unknown command: move_joint") explains itself instead.
    if (error.status === 404 && (!error.explained || error.message === "not found"))
      return "This robot's Cortex doesn't support app commands yet.";
    return `${error.message} (HTTP ${error.status})`;
  }
  if (error instanceof TypeError) return `Could not reach the robot: ${error.message}`;
  return error instanceof Error ? error.message : String(error);
}
