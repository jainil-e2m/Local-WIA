import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { BarChart, PieChart, TreemapChart } from 'echarts/charts';
import { AriaComponent, GraphicComponent, GridComponent, TitleComponent, TooltipComponent } from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';

/*
 * The one Apache ECharts entry point. Only the pieces we use are registered (tree-shaken), rendered as SVG so text
 * stays crisp and the single-file HTML exports keep working. Colours come from the validated categorical palette
 * below (dataviz checker: CVD + normal-vision separation); never use ECharts' default palette.
 */
echarts.use([BarChart, PieChart, TreemapChart, AriaComponent, GraphicComponent, GridComponent, TitleComponent, TooltipComponent, SVGRenderer]);

export type ChartOption = echarts.EChartsCoreOption;
export const CHART_FONT = "'Poppins', system-ui, sans-serif";
/** Fixed categorical order: assign by slot, never cycle. Past 7, fold into a neutral "Other". */
export const PALETTE = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6'];
export const NEUTRAL = '#a8b4c8';
export const INK = { primary: '#1f3a63', secondary: '#4f6489', muted: '#8090ab', grid: '#edf1f8', axis: '#d9e1ef' };

/** Shared tooltip look, matching the KB's cards. */
export const TOOLTIP = {
  backgroundColor: '#fff', borderColor: '#dfe6f4', borderWidth: 1, padding: [9, 12],
  textStyle: { color: INK.secondary, fontFamily: CHART_FONT, fontSize: 11 },
  extraCssText: 'border-radius:10px;box-shadow:0 8px 26px rgba(31,58,99,.12);',
};

export const tooltipRow = (color: string, label: string, value: string) =>
  `<div style="display:flex;align-items:center;gap:7px;margin-top:3px"><span style="width:9px;height:9px;border-radius:3px;background:${color}"></span><span>${label}</span><b style="margin-left:auto;padding-left:14px;color:${INK.primary}">${value}</b></div>`;
export const escapeHtml = (text: string) => text.replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]!);

type Handler = (params: { name: string; dataIndex: number; seriesName?: string; data?: unknown }) => void;

export default function EChart({ option, height, label, onClick, className = '' }: { option: ChartOption; height: number; label: string; onClick?: Handler; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<ReturnType<typeof echarts.init> | null>(null);
  const clickRef = useRef(onClick);
  clickRef.current = onClick;

  useEffect(() => {
    const instance = echarts.init(ref.current!, undefined, { renderer: 'svg' });
    chart.current = instance;
    instance.on('click', params => clickRef.current?.(params as Parameters<Handler>[0]));
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(ref.current!);
    return () => { observer.disconnect(); instance.dispose(); chart.current = null; };
  }, []);

  useEffect(() => {
    // The height may have changed in the same render: size first, or the layout uses the old box and is
    // then resized mid-animation (a treemap ends up half-drawn at the old height).
    chart.current?.resize();
    chart.current?.setOption({
      aria: { enabled: true, label: { description: label } },
      textStyle: { fontFamily: CHART_FONT },
      animationDuration: 450,
      ...option,
    }, true);
  }, [option, label]);

  return <div ref={ref} className={`echart ${className}`} style={{ height, cursor: onClick ? 'pointer' : undefined }} />;
}
