import { ReelScript } from '../types/atelier';

const wordCount = (text: string) => text.trim().split(/\s+/).filter(Boolean).length;

/** Expand short v1 drafts once; preserve already-expanded scripts and saved shot plans. */
export function reelProduction(reel: ReelScript, index: number) {
  const sentence = (text: string) => {
    const clean = text.trim().replace(/^[•\-]\s*/, '');
    return /[.!?…”"]$/.test(clean) ? clean : `${clean}.`;
  };
  const points = reel.talkingPoints.filter(point => !/^Use a fictional example|make no unverified performance claims/i.test(point.trim()));
  const lines = [...new Set([reel.hook, ...points].map(text => text.trim()).filter(Boolean))];
  const mock = reel.id.startsWith('mock-editorial');
  const bridge = [
    'It is easy to keep doing what feels familiar. But before you repeat the same process, ask whether it actually answers the question your client is trying to solve.',
    'Here is how I would approach that conversation. Start with what the couple needs to understand, then explain the decision clearly. The goal is a useful conversation, not a longer sales pitch.',
    'Try this before your next client call. Pick one recent inquiry and write down the question you could have asked earlier. Make that question part of your next conversation, then notice what becomes clearer.',
  ][index % 3];
  const original = reel.spokenScript ?? [...lines.map(sentence), ...(mock ? [bridge] : []), sentence(reel.ctaText)].join('\n\n');
  let spokenScript = original;
  if (reel.spokenScriptVersion !== 2) {
    const additions = [
      [
        'Here is the part I want you to question. More activity can feel like progress, especially when you are busy running a wedding business. But attention and a clear buying decision are not the same thing.',
        'Think about the last inquiry that went quiet. Before adding another task to your marketing list, ask what that couple still needed to understand. Was your value clear? Did they know what would happen next?',
        'That is a more useful starting point than copying what another studio is doing. Your work, your clients, and the conversations you want to have should shape the message. A familiar tactic is not automatically the right tactic.',
      ],
      [
        'Let me make that practical. Imagine a couple reaches out after seeing your work, but they are not sure whether your service fits their plans. Instead of sending everything at once, help them understand one decision first.',
        'Explain what matters, show a relevant example, and make the next step easy to follow. You are not trying to overwhelm them with information. You are giving them enough context to have a better conversation with you.',
        'Notice the difference: the message is built around the question the couple is asking, not just the list of services you sell. That gives your expertise somewhere specific to land, without needing a louder sales pitch.',
      ],
      [
        'Make this small enough that you can actually do it today. Open one recent inquiry and read your reply from the couple’s perspective. What question did you answer clearly, and what did you assume they already understood?',
        'Now change one thing. That might be a clearer explanation, a relevant example, or a simple question before the next step. Keep the rest of the conversation consistent so you can see whether that change was helpful.',
        'After the next few conversations, look beyond views and likes. Are people asking better questions? Do they understand the next step? Those observations will tell you more than adding another task without knowing what you want it to improve.',
      ],
    ][index % 3];
    const shared = [
      'You do not have to rebuild your whole business around this idea. Start with one part of the client journey, keep the language true to your studio, and make the experience easier to understand. Then review what actually happens.',
      'And remember, a useful message does not need a dramatic promise. Be specific about the problem, honest about what you can help with, and clear about the invitation. That is something you can repeat without losing your own voice.',
      'If you are unsure where to start, ask someone outside your business to read the message. Have them explain the next step back to you. Any hesitation gives you a practical place to improve the conversation before you publish it.',
    ];
    const target = Math.max(100, wordCount(original) * 2);
    const cta = sentence(reel.ctaText);
    const ending = original.endsWith(cta) ? cta : original.endsWith(reel.ctaText.trim()) ? reel.ctaText.trim() : '';
    const body = ending ? original.slice(0, -ending.length).trim() : original;
    const expanded = [body];
    for (const paragraph of [...additions, ...shared]) {
      if (wordCount([...expanded, cta].join(' ')) >= target) break;
      expanded.push(paragraph);
    }
    spokenScript = [...expanded, cta].join('\n\n');
  }
  const words = wordCount(spokenScript);
  const duration = `About ${Math.ceil(words / 170 * 60)}–${Math.ceil(words / 145 * 60)} seconds · ${words} words`;
  const visualSequence = reel.visualSequence ?? [
    { beat: 'Opening · Hook', direction: `${reel.visualCue} Start with direct eye contact and a short on-screen headline matching the hook. Keep captions inside the safe area.` },
    { beat: 'Main message', direction: ['Use a restrained split-screen contrast between the common assumption and the better perspective. Return to the speaker for the key sentence.', 'Show the process being explained: hands working through a sample inquiry or checklist. Label the example as illustrative, and hide all client information.', 'Film a close-up of one action being completed on a sample checklist. Add a single numbered text cue so the step is easy to follow.'][index % 3] },
    { beat: 'Supporting footage', direction: 'Cut briefly to relevant wedding details, a workspace, or approved portfolio footage. Use your own or licensed assets; do not present staged footage as evidence of client results.' },
    { beat: 'Closing · Call to action', direction: 'Return to the speaker, then hold a clean branded end frame with the call to action. Use subtle movement and legible captions rather than distracting transitions.' },
  ];
  return { spokenScript, spokenScriptVersion: 2, duration, visualSequence };
}
