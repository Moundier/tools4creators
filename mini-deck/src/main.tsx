import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import Panel from "./Panel";
import ImageSearch from "./ImageSearch";
import { getCurrentWindow } from "@tauri-apps/api/window";

const label = getCurrentWindow().label;
const Root = label === "panel" ? Panel : label === "images" ? ImageSearch : App;
document.documentElement.dataset.window = label;

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode><Root /></React.StrictMode>,
);
