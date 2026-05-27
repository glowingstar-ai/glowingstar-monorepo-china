import type { Metadata } from "next";
import Image from "next/image";
import { teamLogoList } from "@/lib/site-content";

const CONTACT_EMAIL = "1141599642@qq.com";
const CONTACT_HREF = `mailto:${CONTACT_EMAIL}`;

const paperTextureSvg = `
  <svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="0 0 240 240">
    <defs>
      <filter id="paper-clouds">
        <feTurbulence
          type="fractalNoise"
          baseFrequency="0.055"
          numOctaves="2"
          seed="4"
          stitchTiles="stitch"
        />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <filter id="paper-grain">
        <feTurbulence
          type="fractalNoise"
          baseFrequency="0.92"
          numOctaves="3"
          seed="11"
          stitchTiles="stitch"
        />
        <feColorMatrix type="saturate" values="0" />
      </filter>
    </defs>
    <rect width="240" height="240" fill="#f4eee2" />
    <rect width="240" height="240" filter="url(#paper-clouds)" opacity="0.12" />
    <rect width="240" height="240" filter="url(#paper-grain)" opacity="0.08" />
    <g
      transform="rotate(-8 120 120)"
      fill="none"
      stroke="#b19b7a"
      stroke-linecap="round"
      stroke-width="0.65"
      opacity="0.22"
    >
      <path d="M-20 28 C 36 10 72 40 126 22 S 206 12 268 30" />
      <path d="M-24 64 C 22 42 70 76 128 58 S 208 52 272 72" />
      <path d="M-18 104 C 40 84 78 120 136 98 S 212 92 274 112" />
      <path d="M-24 142 C 26 122 72 154 132 138 S 214 128 278 148" />
      <path d="M-16 182 C 34 164 82 198 142 176 S 220 170 282 190" />
      <path d="M-20 220 C 38 200 84 232 144 214 S 224 208 286 228" />
    </g>
    <g
      transform="rotate(-8 120 120)"
      fill="none"
      stroke="#fffaf1"
      stroke-linecap="round"
      stroke-width="0.8"
      opacity="0.25"
    >
      <path d="M8 18 C 58 8 110 28 162 12 S 226 14 258 8" />
      <path d="M14 88 C 56 74 116 102 172 82 S 226 80 260 92" />
      <path d="M0 154 C 46 142 104 164 158 146 S 220 146 252 160" />
      <path d="M4 208 C 54 194 112 220 166 202 S 224 198 258 214" />
    </g>
  </svg>
`
  .trim()
  .replace(/\s{2,}/g, " ");

const paperTextureDataUri = `url("data:image/svg+xml,${encodeURIComponent(
  paperTextureSvg
)}")`;

export const homeMetadata: Metadata = {
  title: "GlowingStar",
  description:
    "AI原生工作流系统，私有内测中，与合作伙伴一对一交付。",
};

export default function HomeLandingPage(): JSX.Element {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#ede6d9] text-[#17120f]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.92),transparent_54%),linear-gradient(180deg,#f5efe3_0%,#ece2d2_48%,#e7ddce_100%)]" />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          backgroundImage:
            "radial-gradient(circle at top left, rgba(255,255,255,0.55), transparent 34%), radial-gradient(circle at bottom right, rgba(154,130,99,0.14), transparent 28%), linear-gradient(180deg, rgba(255,255,255,0.28), rgba(237,230,217,0.08) 46%, rgba(188,168,142,0.12) 100%)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-55"
        style={{
          backgroundImage: paperTextureDataUri,
          backgroundRepeat: "repeat",
          backgroundSize: "240px 240px",
        }}
      />

      <main className="relative mx-auto flex min-h-screen w-full max-w-5xl items-center px-6 py-20 sm:px-10 sm:py-24 lg:py-28">
        <div className="w-full space-y-8">
          <section className="rounded-[2rem] border border-[#17120f]/12 bg-[linear-gradient(180deg,rgba(252,247,239,0.9),rgba(245,237,225,0.94))] px-6 py-8 shadow-[0_20px_60px_rgba(93,66,35,0.08)] sm:px-8">
            <div className="inline-flex items-center gap-3">
              <Image
                src="/logo.png"
                alt="GlowingStar"
                width={40}
                height={40}
                priority
                className="h-10 w-10 object-contain drop-shadow-[0_4px_12px_rgba(235,179,43,0.18)]"
              />
              <p className="font-heading text-xs uppercase tracking-[0.34em] text-[#17120f]/45">
                AI原生工作流
              </p>
            </div>
            <h1 className="mt-5 max-w-3xl font-heading text-4xl leading-tight sm:text-5xl">
              联系我们
            </h1>
            <p className="mt-5 max-w-3xl text-lg leading-8 text-[#17120f]/72 sm:text-xl sm:leading-9">
              GlowingStar 构建AI原生工作流系统。目前处于私有内测阶段，与每个团队进行一对一合作，交付最佳成果。
            </p>
            <p className="mt-4 max-w-3xl text-base leading-8 text-[#17120f]/68 sm:text-[1.05rem]">
              如果您有兴趣与我们合作，请发送邮件至{" "}
              <a
                href={CONTACT_HREF}
                className="font-medium text-[#17120f] underline decoration-[#17120f]/30 underline-offset-4"
              >
                {CONTACT_EMAIL}
              </a>
              。
            </p>
          </section>

          <section className="rounded-[2rem] border border-[#17120f]/12 bg-[linear-gradient(180deg,rgba(252,247,239,0.86),rgba(245,237,225,0.92))] px-6 py-8 shadow-[0_20px_60px_rgba(93,66,35,0.08)] sm:px-8">
            <p className="text-xs uppercase tracking-[0.34em] text-[#17120f]/58">
              团队来自
            </p>
            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {teamLogoList.map((logo) => (
                <div
                  key={logo.alt}
                  className="flex h-20 items-center justify-center rounded-2xl border border-[#17120f]/8 bg-[rgba(255,252,247,0.78)] px-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.78),0_18px_35px_rgba(87,63,35,0.08)]"
                >
                  <Image
                    src={logo.src}
                    alt={logo.alt}
                    width={120}
                    height={48}
                    loading="eager"
                    className={`max-h-10 w-auto object-contain opacity-100 ${logo.className ?? ""} ${"imageClassName" in logo ? logo.imageClassName ?? "" : ""}`}
                  />
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
