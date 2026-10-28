import { Game } from "./game/Game";

const app = document.getElementById("app");
const hud = document.getElementById("hud");
if (!app || !hud) throw new Error("index.html is missing #app or #hud");

new Game(app, hud).start();
