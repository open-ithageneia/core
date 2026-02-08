import { useState } from 'react';

type MapClickQuizProps = {
  maxWidth?: number; // μέγιστο πλάτος container
  points: MapPoint[]; // σημεία που προβάλλονται (user ή canonical)
  setPoints: React.Dispatch<React.SetStateAction<MapPoint[]>>; // setter από parent
  maxPoints: number; // πόσα σημεία επιτρέπονται συνολικά
};

type MapPoint = {
  x: number; // ποσοστό X (0–100)
  y: number; // ποσοστό Y (0–100)
  label: string; // κείμενο (προς το παρόν δεν βαθμολογείται)
};

// component: δείχνει χάρτη + overlay για click
const MapClickQuiz = ({ maxWidth = 900, points, setPoints, maxPoints }: MapClickQuizProps) => {
  // προσωρινό σημείο (όσο γράφουμε πριν το submit)
  const [draftPoint, setDraftPoint] = useState<{ x: number; y: number } | null>(null);

  // προσωρινό label για το draft σημείο
  const [label, setLabel] = useState('');

  // click πάνω στο overlay
  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // αν υπάρχει ήδη draft ή έχουμε φτάσει το max, μπλοκάρουμε
    if (draftPoint || points.length >= maxPoints) return;

    const rect = e.currentTarget.getBoundingClientRect();

    // ΧΡΗΣΙΜΟ: clientX/Y – rect.left/top
    const xPercentage = ((e.clientX - rect.left) / rect.width) * 100;
    const yPercentage = ((e.clientY - rect.top) / rect.height) * 100;

    setDraftPoint({ x: xPercentage, y: yPercentage });
    setLabel('');
  };

  const handleSubmit = () => {
    if (!draftPoint || !label.trim()) return;

    // προσθέτουμε το σημείο στο state του parent
    setPoints((prev) => [...prev, { x: draftPoint.x, y: draftPoint.y, label }]);

    // καθαρίζουμε μόνο το draft
    setDraftPoint(null);
    setLabel('');
  };

  const handleCancelDraft = () => {
    setDraftPoint(null);
    setLabel('');
  };

  const updatePointLabel = (index: number, value: string) => {
    setPoints((prev) => prev.map((p, i) => (i === index ? { ...p, label: value } : p)));
  };

  const removePoint = (index: number) => {
    // αν ακυρώσουμε ένα σημείο, ελευθερώνεται slot
    setPoints((prev) => prev.filter((_, i) => i !== index));
  };

  // styles για input + label (ίδια πριν & μετά submit)
  const compactInputStyle = {
    width: 70,
    height: 18,
    fontSize: 11,
    padding: '1px 3px',
    border: '1px solid #aaa',
    borderRadius: 3,
    outline: 'none',
  };

  const compactBoxStyle = {
    display: 'flex',
    gap: 3,
    background: 'white',
    padding: '2px 3px',
    border: '1px solid #ccc',
    borderRadius: 4,
    zIndex: 10,
  };

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        maxWidth,
      }}
    >
      {/* χάρτης */}
      <img
        src="/static/mapOfGreecce.png"
        alt="Χάρτης Ελλάδας"
        style={{
          width: '100%',
          height: 'auto',
          display: 'block',
        }}
      />

      {/* overlay για click – ΙΔΙΟ container με τα points */}
      <div
        onClick={handleClick}
        style={{
          position: 'absolute',
          inset: 0,
          cursor: draftPoint || points.length >= maxPoints ? 'not-allowed' : 'crosshair',
        }}
      />

      {/* ήδη υποβληθέντα σημεία */}
      {points.map((p, index) => (
        <div key={index}>
          {/* κουκίδα */}
          <div
            style={{
              position: 'absolute',
              left: `${p.x}%`,
              top: `${p.y}%`,
              transform: 'translate(-50%, -50%)',
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: 'red',
              pointerEvents: 'none',
            }}
          />

          {/* label δίπλα στην κουκίδα */}
          <div
            style={{
              position: 'absolute',
              left: `${p.x}%`,
              top: `${p.y}%`,
              transform: 'translate(10px, -50%)',
              ...compactBoxStyle,
            }}
          >
            <input
              type="text"
              value={p.label}
              onChange={(e) => updatePointLabel(index, e.target.value)}
              placeholder="γράψε"
              style={compactInputStyle}
            />

            <button style={{ fontSize: 11 }} onClick={() => removePoint(index)}>
              ✖
            </button>
          </div>
        </div>
      ))}

      {/* draft κουκίδα + input */}
      {draftPoint && (
        <>
          <div
            style={{
              position: 'absolute',
              left: `${draftPoint.x}%`,
              top: `${draftPoint.y}%`,
              transform: 'translate(-50%, -50%)',
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: 'blue',
              pointerEvents: 'none',
            }}
          />

          <div
            style={{
              position: 'absolute',
              left: `${draftPoint.x}%`,
              top: `${draftPoint.y}%`,
              transform: 'translate(10px, -50%)',
              ...compactBoxStyle,
            }}
          >
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="γράψε"
              style={compactInputStyle}
            />

            <button style={{ fontSize: 11 }} onClick={handleSubmit}>
              ✔
            </button>
            <button style={{ fontSize: 11 }} onClick={handleCancelDraft}>
              ✖
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default MapClickQuiz;
