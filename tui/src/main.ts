import {
  createStdinDriver,
  createStdoutRenderer,
  createTerminalApp,
  installTerminalCleanup,
} from "@simon_he/vue-tui/cli";
import { App } from "./app.js";

const COLS = Number.isFinite(process.stdout.columns) ? process.stdout.columns! : 100;
const ROWS = Number.isFinite(process.stdout.rows) ? process.stdout.rows! : 30;

const app = createTerminalApp({
  cols: COLS,
  rows: ROWS,
  component: App,
  defaultStyle: { fg: "whiteBright" },
});
app.mount();

const renderer = createStdoutRenderer(app.terminal, {
  output: process.stdout,
  hideCursor: true,
  colorMode: "auto",
});

const cleanup = () => {
  driver?.dispose();
  renderer.dispose();
  app.dispose();
};

const cleanupHandle = installTerminalCleanup(cleanup);

const driver = createStdinDriver({
  dispatch(event) {
    const prevented = app.events.dispatch(event);
    app.scheduler.flush();
    return prevented;
  },
  enableMouse: true,
  onExit() {
    cleanupHandle.cleanup();
    process.exit(0);
  },
});

app.scheduler.flushNow();
