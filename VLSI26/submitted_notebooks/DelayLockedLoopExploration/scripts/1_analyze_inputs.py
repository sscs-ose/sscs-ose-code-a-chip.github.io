import math
import argparse

VALID_DELAYS = [600, 700]
LOCK_COUNT_MIN = 2

def validate_and_recommend(clk, ctrl, init, delay, update_div):
    clk_ps = clk * 1000
    stages = 2 ** ctrl
    total_delay = stages * delay

    # Tolerance calculation (matches TB)
    delay_ns = delay * 1e-3
    tol_ns = min(1.5 * delay_ns, 0.25 * clk)
    tol_ps = tol_ns * 1000

    print("\n====================================")
    print("DLL CONFIG CHECK")
    print("====================================")

    print(f"CLK_PERIOD       = {clk} ns ({clk_ps} ps)")
    print(f"CTRL_BITS        = {ctrl} (stages={stages})")
    print(f"INIT_CTRL        = {init}")
    print(f"DELAY_PS         = {delay}")
    print(f"UPDATE_DIV_BITS  = {update_div}")

    print("\n--- DERIVED ---")
    print(f"Total delay range = {total_delay:.1f} ps ({total_delay/1000:.3f} ns)")
    print(f"Tolerance (tol)   = {tol_ps:.1f} ps ({tol_ns:.3f} ns)")
    print(f"  = min(1.5×delay, 0.25×clk)")

    print("\n--- VALIDATION ---")

    valid = True

    # ---- DELAY CHECK ----
    if delay not in VALID_DELAYS:
        print(f"❌ ERROR: DELAY_PS must be one of {VALID_DELAYS}")
        valid = False

    # ---- LOCK RANGE CHECK (UPDATED) ----
    min_needed = clk_ps - tol_ps

    if total_delay < min_needed:
        print("❌ ERROR: Cannot lock")
        print(f"   Delay range too small considering tolerance")
        print(f"   Needed ≥ {min_needed:.1f} ps")
        print(f"   Got    = {total_delay:.1f} ps")

        needed_ctrl = math.ceil(math.log2(min_needed / delay))
        print(f"   👉 Increase CTRL_BITS to ≥ {needed_ctrl}")
        valid = False
    else:
        print("✅ Delay range sufficient for locking")

    # ---- INIT CTRL CHECK ----
    if not (0 <= init < stages):
        print("❌ ERROR: INIT_CTRL out of range")
        print(f"   Must be between 0 and {stages-1}")
        valid = False
    else:
        print("✅ INIT_CTRL in valid range")

    # ---- UPDATE DIV CHECK ----
    if update_div < 2:
        print("❌ ERROR: UPDATE_DIV_BITS must be ≥ 2")
        valid = False
    else:
        print("✅ UPDATE_DIV_BITS valid")

    # ---- QUALITY CHECKS ----
    print("\n--- QUALITY ---")

    # Total delay quality
    if total_delay > 2 * clk_ps:
        print("⚠️  WARNING: Delay range is excessive (slow convergence)")
    elif total_delay < clk_ps:
        print("⚠️  WARNING: Barely enough delay range")

    # INIT quality
    ideal_init = stages // 2
    if abs(init - ideal_init) > stages * 0.25:
        print(f"⚠️  WARNING: INIT_CTRL far from center (recommended ≈ {ideal_init})")
    else:
        print("✅ INIT_CTRL well centered")

    # UPDATE_DIV heuristic
    recommended_update = max(2, ctrl - 4)
    if update_div != recommended_update:
        print(f"⚠️  WARNING: UPDATE_DIV_BITS not ideal")
        print(f"   👉 Recommended ≈ {recommended_update}")

    # Resolution check
    resolution = delay / clk_ps
    print(f"Resolution = {resolution*100:.2f}% of clock")

    if resolution > 0.25:
        print("❌ ERROR: Resolution too coarse")
        valid = False
    elif resolution > 0.15:
        print("⚠️  WARNING: Coarse resolution")

    # ---- FINAL STATUS ----
    print("\n====================================")

    if valid:
        print("✅ VALID CONFIG")
    else:
        print("❌ INVALID CONFIG")

    print("====================================\n")

    # ---- RECOMMENDATIONS ----
    print("RECOMMENDATIONS:")

    print(f"- CTRL_BITS ≥ {math.ceil(math.log2(clk_ps / delay))}")
    print(f"- INIT_CTRL ≈ {ideal_init}")
    print(f"- UPDATE_DIV_BITS ≈ {recommended_update}")
    print(f"- Tolerance used = min(1.5×DELAY, 0.25×CLK)")
    print(f"- DELAY_PS ∈ {VALID_DELAYS}")
    print("====================================\n")

    
def main():
    parser = argparse.ArgumentParser(description="DLL Config Validator")

    parser.add_argument("--clk", type=float, required=True)
    parser.add_argument("--ctrl", type=int, required=True)
    parser.add_argument("--init", type=int, required=True)
    parser.add_argument("--delay", type=int, required=True)
    parser.add_argument("--update", type=int, required=True)

    args = parser.parse_args()

    validate_and_recommend(
        clk=args.clk,
        ctrl=args.ctrl,
        init=args.init,
        delay=args.delay,
        update_div=args.update
    )


if __name__ == "__main__":
    main()