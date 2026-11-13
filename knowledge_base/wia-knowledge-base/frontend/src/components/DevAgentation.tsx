import { useEffect, useState } from 'react';
import { Agentation } from 'agentation';

/** Local-only feedback, using the same copy/paste workflow as Content Atelier. */
export default function DevAgentation() {
  const [portalContainer, setPortalContainer] = useState<HTMLDialogElement | null>(null);

  useEffect(() => {
    // Native modal dialogs make the rest of the document inert. Keep the toolbar
    // inside the active dialog so drawers and forms can also be annotated.
    const updateContainer = () => {
      const dialogs = document.querySelectorAll<HTMLDialogElement>('dialog[open]');
      setPortalContainer(dialogs.item(dialogs.length - 1));
    };
    updateContainer();
    const observer = new MutationObserver(updateContainer);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['open'],
    });
    return () => observer.disconnect();
  }, []);

  return <Agentation appName="WIA Client Knowledge Base" useHashLocation portalContainer={portalContainer} />;
}
