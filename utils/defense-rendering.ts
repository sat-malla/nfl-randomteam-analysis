type PlayerLike = { position: string; name: string; [key: string]: unknown };

const LB_TYPES = new Set(["LB", "ILB", "OLB", "MLB", "SLB", "WLB"]);

export function assignLbLabels<T extends PlayerLike>(players: T[], defenseType?: string): T[] {
  const is34 = defenseType?.includes("3-4") ?? false;
  const genericLbs = players.filter((p) => p.position === "LB");
  const total = genericLbs.length;
  let lbIdx = 0;

  return players.map((p) => {
    if (is34 && p.position === "DT") return { ...p, position: "NT" };
    if (p.position !== "LB") return p;
    let label: string;
    if (is34) {
      if (total <= 2) {
        label = lbIdx === 0 ? "OLB" : "OLB";
      } else {
        label = (lbIdx === 0 || lbIdx === total - 1) ? "OLB" : "ILB";
      }
    } else {
      if (total <= 1) {
        label = "MLB";
      } else if (total === 2) {
        label = lbIdx === 0 ? "SLB" : "WLB";
      } else {
        if (lbIdx === 0) label = "SLB";
        else if (lbIdx === total - 1) label = "WLB";
        else label = "MLB";
      }
    }
    lbIdx++;
    return { ...p, position: label };
  });
}

export { LB_TYPES };
