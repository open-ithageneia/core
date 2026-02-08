// frontend\src\geo\finalTestComponent\GeoMapQuestionInstance.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import MapClickQuiz from "../components/MapClickQuiz";
import GeoGradingSummary from "../components/GeoGradingSummary";
import { getCanonicalPoints } from "../utils/geoQuestionUtils";
import { buildReviewPoints, gradePoints } from "../utils/geoGrading";
import type { GeoQuestion, GradedPoint, MapPoint } from "../types/geoTypes";

export type GeoMapQuestionInstanceProps = {
  // η ερώτηση που πρέπει να απαντηθεί (έρχεται απ’ έξω)
  question: GeoQuestion;

  // callback που καλείται στο submit
  onSubmit: (result: {
    gradedPoints: GradedPoint[];
    score: number;
    maxScore: number;
    userPoints: MapPoint[];
  }) => void;
};

const GeoMapQuestionInstance = ({
  question,
  onSubmit,
}: GeoMapQuestionInstanceProps) => {
  const [points, setPoints] = useState<MapPoint[]>([]);
  const [gradedPoints, setGradedPoints] = useState<GradedPoint[] | null>(null);
  const [displayPoints, setDisplayPoints] = useState<MapPoint[]>([]);

  const handleSubmit = () => {
    if (!question.canonicalAnswer) return;

    const tolerance = question.rules?.tolerancePct ?? 3.5;

    const graded = gradePoints(
      points,
      question.canonicalAnswer.points,
      tolerance,
    );

    const canonicalPoints = getCanonicalPoints(question);
    const reviewPoints = buildReviewPoints(graded, canonicalPoints, tolerance);

    setGradedPoints(graded);
    setDisplayPoints(reviewPoints);

    onSubmit({
      gradedPoints: graded,
      score: graded.filter((p) => p.correct && p.labelCorrect).length,
      maxScore: question.rules?.maxPoints ?? graded.length,
      userPoints: points,
    });
  };

  return (
    <div className="space-y-4">
      <MapClickQuiz
        points={gradedPoints ? displayPoints : points}
        setPoints={setPoints}
        maxPoints={question.rules?.maxPoints ?? 4}
      />

      <Button
        onClick={handleSubmit}
        disabled={points.length === 0}
        className="bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        Submit
      </Button>

      {gradedPoints && (
        <GeoGradingSummary gradedPoints={gradedPoints} question={question} />
      )}
    </div>
  );
};

export default GeoMapQuestionInstance;
