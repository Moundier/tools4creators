import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import Panel from "./Panel";
import { getCurrentWindow } from "@tauri-apps/api/window";

const label = getCurrentWindow().label;
const isPanel = label === "panel";
document.documentElement.dataset.window = label;

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>{isPanel ? <Panel /> : <App />}</React.StrictMode>,
);
