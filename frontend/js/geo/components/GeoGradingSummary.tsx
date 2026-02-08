import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { GradedPoint, GeoQuestion } from "../types/geoTypes";

type GeoGradingSummaryProps = {
  gradedPoints: GradedPoint[];
  question: GeoQuestion | null;
};

const GeoGradingSummary = ({
  gradedPoints,
  question,
}: GeoGradingSummaryProps) => {
  const fullyCorrect = gradedPoints.filter(
    (p) => p.correct && p.labelCorrect,
  ).length;

  const spatialCorrect = gradedPoints.filter((p) => p.correct).length;

  const maxPoints = question?.rules?.maxPoints ?? gradedPoints.length;

  return (
    <Card className="mt-3">
      <CardContent>
        {/* Τίτλος */}
        <h3 className="mb-2 text-lg font-semibold text-foreground">
          Αξιολόγηση
        </h3>

        {/* Summary */}
        <div className="mb-2 flex gap-2">
          <Badge
            className={
              fullyCorrect === maxPoints
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground"
            }
          >
            Πλήρως σωστά: {fullyCorrect} / {maxPoints}
          </Badge>

          <Badge className="bg-secondary text-secondary-foreground">
            Χωρικά σωστά: {spatialCorrect}
          </Badge>
        </div>
        <div className="mb-2 border-b border-border" />

        {/* Λεπτομέρειες */}
        <ul className="space-y-2">
          {gradedPoints.map((p, i) => (
            <li key={i} className="rounded-md border border-border bg-card p-2">
              <p className="text-sm font-medium text-foreground">
                {i + 1}. ({p.x.toFixed(2)}, {p.y.toFixed(2)}) → “{p.label}”
              </p>

              <div className="mt-1 flex gap-1">
                <Badge
                  className={
                    p.correct
                      ? "bg-primary text-primary-foreground"
                      : "bg-destructive text-white"
                  }
                >
                  {p.correct ? "σωστό σημείο" : "λάθος σημείο"}
                </Badge>

                <Badge
                  className={
                    p.labelCorrect
                      ? "bg-secondary text-secondary-foreground"
                      : "bg-destructive text-white"
                  }
                >
                  {p.labelCorrect
                    ? p.hasSpellingErrors
                      ? "σωστό με ορθογραφικά"
                      : "σωστό λεκτικό"
                    : "λάθος λεκτικό"}
                </Badge>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
};

export default GeoGradingSummary;
