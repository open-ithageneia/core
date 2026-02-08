export const simplifyLang = (input: string): string => {
  let s = input.toLowerCase().trim();

  // αφαίρεση τόνων
  s = s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");

  // αφαίρεση σημείων στίξης & κενών
  s = s.replace(/[^a-zα-ω0-9]/g, "");

  // ενοποιήσεις φωνηέντων
  s = s
    .replace(/η|ι|υ|ει|οι|υι/g, "ι")
    .replace(/ο|ω/g, "ο")
    .replace(/ε|αι/g, "ε");

  // greeklish (βασική, επεκτείνεται)
  s = s
    .replace(/θ/g, "th")
    .replace(/χ/g, "x")
    .replace(/ψ/g, "ps")
    .replace(/ξ/g, "ks")
    .replace(/γ/g, "g")
    .replace(/δ/g, "d")
    .replace(/κ/g, "k")
    .replace(/λ/g, "l")
    .replace(/μ/g, "m")
    .replace(/ν/g, "n")
    .replace(/π/g, "p")
    .replace(/ρ/g, "r")
    .replace(/σ|ς/g, "s")
    .replace(/τ/g, "t")
    .replace(/φ/g, "f")
    .replace(/β/g, "v")
    .replace(/ζ/g, "z")
    .replace(/α/g, "a")
    .replace(/ε/g, "e")
    .replace(/ι/g, "i")
    .replace(/ο/g, "o")
    .replace(/υ/g, "u")
    .replace(/η/g, "i")
    .replace(/ω/g, "o");

  return s;
};
