import { useEffect, useRef, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { openUrl } from "@tauri-apps/plugin-opener";
import { Icon } from "./icons";
import "./Panel.css";
import "./ImageSearch.css";

// udm=2 is the Images tab; tbs filters to transparent background PNG files.
function googleImagesUrl(query: string) {
  const params = new URLSearchParams({ q: query, udm: "2", tbs: "ic:trans,ift:png" });
  return `https://www.google.com/search?${params}`;
}

function ImageSearch() {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const unlisten = getCurrentWindow().onFocusChanged(({ payload: focused }) => {
      if (focused) inputRef.current?.select();
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  async function search() {
    const q = query.trim();
    if (!q) return;
    await openUrl(googleImagesUrl(q));
    await getCurrentWindow().hide();
  }

  return (
    <div className="panel" onKeyDown={(e) => e.key === "Escape" && getCurrentWindow().hide()}>
      <header data-tauri-drag-region>
        <h1 data-tauri-drag-region>Images</h1>
        <button className="close" title="Close" onClick={() => getCurrentWindow().hide()}>
          <Icon name="close" />
        </button>
      </header>

      <form
        className="group search"
        onSubmit={(e) => {
          e.preventDefault();
          search();
        }}
      >
        <Icon name="search" />
        <input
          ref={inputRef}
          autoFocus
          value={query}
          placeholder="Search transparent PNGs on Google"
          spellCheck={false}
          onChange={(e) => setQuery(e.target.value)}
        />
      </form>
    </div>
  );
}

export default ImageSearch;
