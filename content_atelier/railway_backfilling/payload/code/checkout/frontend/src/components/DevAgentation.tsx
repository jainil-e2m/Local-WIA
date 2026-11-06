import React from 'react';
import { Agentation } from 'agentation';

/** Local-only annotation tooling. No endpoint or webhook is configured. */
export default function DevAgentation() {
  return <Agentation appName="WIA Content Atelier" />;
}
