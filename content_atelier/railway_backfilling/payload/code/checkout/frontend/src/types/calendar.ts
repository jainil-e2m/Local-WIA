export type CalendarFormat = 'Email' | 'Carousel' | 'Reel';
export interface CalendarEntry {
  id: string;
  ideaId: string;
  day: number;
  channel: CalendarFormat;
  time: string;
  title: string;
  contentOrder?: number;
  warning?: string;
}
