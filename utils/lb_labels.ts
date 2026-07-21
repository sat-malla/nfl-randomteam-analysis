type PlayerLike = { position: string; name: string; [key: string]: unknown };

const LB_TYPES = new Set(["LB", "ILB", "OLB", "MLB"]);

export function assignLbLabels<T extends PlayerLike>(players: T[]): T[] {
  const genericLbs = players.filter((p) => p.position === "LB");
  const total = genericLbs.length;
  let lbIdx = 0;

  return players.map((p) => {
    if (p.position !== "LB") return p;
    let label: string;
    if (total <= 1) {
      label = "MLB";
    } else if (total === 2) {
      label = lbIdx === 0 ? "SLB" : "WLB";
    } else {
      if (lbIdx === 0) label = "SLB";
      else if (lbIdx === total - 1) label = "WLB";
      else label = "MLB";
    }
    lbIdx++;
    return { ...p, position: label };
  });
}

export { LB_TYPES };
