---
name: android-clean-architecture
argument-hint: <action> [feature_name]
description: Apply Clean Architecture to an Android Gradle project, driven by aca.json — generates domain/data/viewmodel/ui/connector layers (MVI, DI hilt/dagger/koin/pure). Use for cross-layer features or first-time scaffolding; not for single-layer work. Triggers: "add a feature", "scaffold the layers", "refactor to clean architecture".
---

## When to use

Apply Clean Architecture to an Android Gradle project, driven by `aca.json`. Generates code across domain/data/viewmodel/ui/connector layers with MVI and configurable DI (hilt/dagger/koin/pure). Trigger when the user says "add a feature", "scaffold the layers", "refactor to clean architecture", or sets up a project with no `aca.json` yet.

When to use: Use when adding a feature that spans layers, scaffolding the first `aca.json`, or restructuring code into the Clean Architecture layout. Do NOT use for work confined to a single layer — go direct to the layer-specific skill (android-unit-test, android-ui-test, etc.).

# Android Clean Architecture

Apply Clean Architecture on an Android Gradle project, driven by `aca.json` at the project root. The skill (1) ensures `aca.json` exists and is correct, then (2) generates / wires code in the layers it defines.

References (load only when the procedure points at them):
- `references/layers.md` — exact package layout for small / medium / large scopes, file naming, where each artifact lives (including connector layer).
- `references/templates.md` — Kotlin templates for state / event / viewmodel / screen / repository / datasource impls / connector interfaces + impls.
- `references/di.md` — DI wiring snippets per library (hilt, dagger, koin, pure), including connector bindings.

**Layers covered (same horizontal floor as data):** `domain` (model + repository + datasource interfaces + connector interfaces), `data` (datasource impls), **`connector` (one module/package per platform integration — vpn, widget, accessibility, live wallpaper, overlay, notification, broadcast receiver, service,...)**, `viewmodel`, `ui`.

**Connector vs Repository — do not confuse:**
- **Repository** lives in `domain` and orchestrates *data* (CRUD, caching, sync between local + remote datasources).
- **Connector** lives at the *same horizontal floor as `data`* (its own module(s) under e.g. `vpn-connector/`, `widget-connector/`, …). It bridges the viewmodel to **Android platform providers**: services, broadcast receivers, overlay views, widget providers, accessibility services, vpn services, notification services, live wallpaper services. It exposes *commands* (turn on, disconnect, trigger wallpaper change, push overlay update) and *observable platform state*, not data persistence.
- A project may have **multiple connectors**, one per platform integration. Each is its own scaffold (`<X>-connector/` module for `large`, `<base>.<x>_connector/` package otherwise) holding the platform component(s) + `<X>ConnectorImp` + `<X>ConnectorModule` (DI).
- A connector **must not** depend on a repository, and a repository **must not** depend on a connector — they are sibling layers. ViewModels may inject either or both.

**Module creation:** whenever this skill needs to create a new Gradle module — `:domain` / `:data` / `:viewmodel` / `:ui` for `large` scope, `:core` for `medium`, **and one `:<x>-connector` module per connector under `large` scope** (e.g. `:vpn-connector`, `:widget-connector`, `:accessibility-connector`) — **you MUST call the `Skill` tool** with `skill: "create-android-module"` and the appropriate `args` string. Do NOT hand-write `build.gradle.kts`, `settings.gradle.kts` entries, or `AndroidManifest.xml` yourself — that skill handles namespace inference, settings registration, and matches existing modules' build patterns. **Always include `--skip-verify` in args** when calling it from this skill — CA scaffolding creates several modules in sequence and the final compile step at the end of the CA flow (Step 2 §4) is the single source of truth for build verification; running gradle sync after every module is wasteful. Only fall back to manual creation if `create-android-module` is unavailable or the user explicitly opts out.

**Connector placement is scope-driven — read this before scaffolding any connector:**
- `scope=large` → **each connector is its own Gradle module** named `:<x>-connector` (kebab-case), sibling of `:data`. The impl class, platform component (service / receiver / provider / etc.), DI module, and `AndroidManifest.xml` registrations all live **inside that connector module**. **Never** put connector impls, platform components, or their manifest entries in `:app` under large scope. `:app` only wires DI and merges manifests.
- `scope=medium` → connector interfaces in `:core`'s `domain/connector/`; connector impls + platform components live in `app/src/main/java/<base>/<x>_connector/` (one package per connector).
- `scope=small` → everything in `app/`, with each connector as its own `<base>.<x>_connector/` package.

If you find yourself about to write a `VpnService`, `BroadcastReceiver`, `AppWidgetProvider`, `AccessibilityService`, `WallpaperService`, or a `*ConnectorImp` class into the `:app` module while `aca.json.scope=large`, **stop** — you are violating the layout. Create the `:<x>-connector` module via `create-android-module --skip-verify` first, then place the files there.

## Step 0 — Confirm Android Gradle project

Abort with a clear message if any are missing:
- `settings.gradle(.kts)` at project root.
- A top-level `build.gradle(.kts)`.
- At least an `app/` module with an `android { ... }` block.

## Step 1 — Resolve `aca.json`

`aca.json` lives at the project root. Schema:

```json
{
  "scope": "small | medium | large",
  "di": "hilt | dagger | koin | pure",
  "mergeViewModelAndScreen": false,
  "useUseCases": true
}
```

Defaults: `scope=large`, `di=koin`, `mergeViewModelAndScreen=false`, `useUseCases=true`.
Constraint: `mergeViewModelAndScreen` is **ignored** (force false) when `scope=large`.

**`useUseCases` flag — controls whether the domain use-case layer exists:**

| `useUseCases` | Effect |
|---|---|
| `true` (default) | Generate `domain/usecase/<feature>/` classes. ViewModels inject use cases, never repositories or connectors directly. Each use case is a single-responsibility `operator fun invoke(...)` class. Wire use cases in DI (Koin `factory`, Hilt `@Provides`, etc.). |
| `false` | **Skip the use-case layer entirely.** Business logic that would live in a use case moves into the ViewModel directly. ViewModels inject **repositories and connectors** (from `domain`) instead. No `usecase/` packages are created; never generate a use-case class when this flag is false. |

When `useUseCases=false` and the user asks to "add feature X", omit the use-case step from the vertical slice and let the ViewModel contain the orchestration logic (calling repository/connector methods, mapping results, combining flows). All other layers (model, repository, datasource, connector, screen) are unaffected.

### Step 1a — If `aca.json` exists

Read it and validate against the schema. If any field is missing or invalid, ask the user once, fix, and rewrite the file. Do not silently apply defaults to an existing config.

### Step 1b — If `aca.json` is missing — new project

Definition of "new project": only an `app` module exists and it contains essentially `MainActivity` plus boilerplate (no `domain` / `data` / feature packages, no extra modules beyond `app`).

For a new project, **ask the user** for each field (offer the defaults). Then:
1. Write `aca.json` at project root.
2. Scaffold the empty layer structure for the chosen scope per `references/layers.md` (create modules / packages but do not generate features yet). **For each new Gradle module, call the `Skill` tool** (`skill: "create-android-module"`, `args: "<module_name> --skip-verify"`) — do NOT write module files by hand.
3. Wire the DI container skeleton per `references/di.md`.

### Step 1c — If `aca.json` is missing — existing project

Inspect the project to infer each field:
- **scope**: count modules. If only `app`, scope is `small` unless domain/data packages exist. If `app` + a `core` module, scope is `medium`. If separate `domain`, `data` (and optionally `viewmodel`, `ui`) modules exist, scope is `large`.
- **di**: grep `build.gradle(.kts)` and source for `hilt`, `dagger`, `koin`. Pick the dominant one. If none found, ask.
- **mergeViewModelAndScreen**: check whether ViewModels and `@Composable` screens for the same feature live in the same package. Only meaningful when scope ≠ large.

Show the user the inferred config, list any properties that are ambiguous, and **ask before writing**. If the project does not follow CA at all, ask: "Refactor toward Clean Architecture per aca.json?" Do not refactor without explicit confirmation.

## Step 2 — Use `aca.json` for every CA action

After Step 1, every code-generation request **must** read `aca.json` first and resolve target locations from `references/layers.md`. Do not hardcode paths.

### Pre-flight gate: connector requests (read before generating any file)

If the request is a connector - request about adding feature related to android platform such as 
accessibility service, android widget, overlay window, etc. Follow this order **strictly** — do not 
skip, reorder, or write any connector file before the module exists:

1. Read `aca.json` → get `scope`.
2. If `scope == "large"`:
   a. Compute module name `<x>-connector` (kebab-case, e.g. `vpn-connector`).
   b. Check whether `:<x>-connector` already exists in `settings.gradle(.kts)`. If it does, skip to step 3.
   c. **Call the `Skill` tool** with `skill: "create-android-module"` and `args: "<x>-connector --skip-verify"`. Do **not** hand-write `build.gradle.kts`, `AndroidManifest.xml`, `settings.gradle.kts` registration, or the module directory yourself. Wait for the skill to finish before continuing.
   d. Verify the module now exists on disk before continuing.
3. Only after the module (large) / package (medium/small) exists, generate the connector interface in `domain`, the impl + platform component + DI module in the connector location, and add manifest entries.
4. Run the compile check from Step 2 §4 once at the end.

If you catch yourself about to `Write` a `build.gradle.kts`, `AndroidManifest.xml`, or a `*Service`/`*Receiver`/`*Provider`/`*ConnectorImp` file under `:app` (or anywhere outside an existing `:<x>-connector` module) while `scope=large`, **stop immediately** and go back to step 2c. Failing to delegate to `create-android-module` is the #1 cause of broken connector layouts.

Supported actions and what they generate:

| User asks | Generate |
|---|---|
| "add feature `X`" | full vertical slice: domain model + repository (interface or concrete per scope), datasource interfaces, **use-case classes** (only when `useUseCases=true`), viewmodel package (state + event + viewmodel), screen + action sealed interface, DI bindings |
| "add viewmodel for `X`" | `XState`, `XEvent`, `XViewModel` in the viewmodel package; wire DI **inside the viewmodel layer** (`<base>.viewmodel.di` package or `:viewmodel` module's `di/`) — never in `data/di` and never in `:app` |
| "add screen for `X`" | `XScreen` composable + `XAction` sealed interface, depending on `mergeViewModelAndScreen` either alongside viewmodel or in the ui package |
| "add repository for `X`" | domain repository (concrete class holding remote + local datasource interfaces), local + remote datasource interfaces, DI binding |
| "add room datasource for `X`" | `XEntity` + `XDao` (with mapper to pure model) + `RoomXDataSource` impl + database registration |
| "add retrofit datasource for `X`" | `XDto` (with mapper) + `XApi` + `RetrofitXDataSource` impl + DI binding |
| "add firestore datasource for `X`" | `FirestoreXDataSource` impl (+ shared `FirestoreExtensions` if missing) + DI binding |
| "add datastore datasource for `X`" | `DataStoreXDataSource` impl + DI binding |
| "add connector for `X`" *(or "add vpn / widget / accessibility / live wallpaper / overlay / notification / broadcast / service connector")* | **Run the connector pre-flight gate above first.** Then: `XConnector` interface in `domain/connector/`, plus a sibling-of-data scaffold holding the platform component(s) (e.g. `AppVpnService`, `ThemeWidgetProvider`), `XConnectorImp`, and `XConnectorModule` for DI, with manifest entries co-located. **Placement by scope:** `large` → inside the `:<x>-connector` module that the pre-flight gate created via the `Skill` tool (`skill: "create-android-module"`, `args: "<x>-connector --skip-verify"`) — NOT in `:app`; `medium` → `<base>.<x>_connector/` package inside `:app`; `small` → `<base>.<x>_connector/` package inside `:app`. |
| "wire DI" | regenerate the DI module(s) per `references/di.md` for the resolved layer placement (repository **and** connector bindings) |

For each action:
1. Resolve package paths via `references/layers.md` using `aca.json`.
2. Generate code from `references/templates.md`. Keep MVI shape: `data class XState`, `sealed interface XEvent`, `class XViewModel(...)` collecting from repositories. Screens take `modifier`, `state`, `onEvent`, `onAction` and define a local `sealed interface XAction`.
3. Update DI per `references/di.md` (Hilt module / Dagger module / Koin module / pure factory). Never leave a new repository or viewmodel un-injected.
4. After every file create/modify, run the project's compile command (e.g. `./gradlew :<module>:compileDebugKotlin` or `./gradlew assembleDebug`) and fix errors before reporting done.

## Naming rules

- Feature packages: `snake_case` (e.g. `movie_list`, `vpn_details`) — matches the user's example.
- Files / classes: `PascalCase` (`MovieListViewModel`, `MovieListScreen`).
- Datasource impls are named after their backing tech: `RoomMovieDataSource`, `RetrofitMovieApi`, `FirestoreMovieDataSource`, `DataStoreUserSettingsDataSource`.
- DAOs include the mapper to the pure-Kotlin domain model in the same file.
- DTOs include the mapper to the pure-Kotlin domain model in the same file.

## Hard rules

- Domain layer **must not** import Android, Room, Retrofit, Firebase, DataStore, or DI library annotations beyond Inject (Hilt/Dagger). Pure Kotlin only.
- Repository concrete class lives in **domain** and depends only on local/remote datasource **interfaces** declared next to it. Implementations of those interfaces live in **data**.
- Connector interfaces live in **domain** (`domain/connector/`); implementations + the platform component (service / receiver / provider / accessibility / overlay) live in their own connector module/package (sibling of `data`). A connector **never** holds or depends on a repository, and a repository never depends on a connector — they are sibling layers. ViewModels may inject connectors directly alongside repositories.
- **Connector module rule for `large` scope (mandatory):** every connector MUST live in a dedicated `:<x>-connector` Gradle module (sibling of `:data`). Connector impl classes, platform components (`*Service`, `*Receiver`, `*Provider`, `*WallpaperService`, `*AccessibilityService`, overlay holders, etc.), DI modules, and their `<service>` / `<receiver>` / `<provider>` manifest entries MUST NOT be placed in `:app`. `:app` only depends on the connector module and merges its manifest. If `aca.json.scope=large` and a connector module does not yet exist, create it via `create-android-module --skip-verify` before generating any connector files.
- ViewModel uses MVI: single `MutableStateFlow<XState>` exposed as `state`, plus an `onEvent: (XEvent) -> Unit` lambda. No `LiveData`, no public mutable state.
- **MVI Event / Action separation (mandatory — see `references/templates.md` §"MVI separation").** `XEvent` lives in `viewmodel/<feature>/` and flows Screen → VM. `XAction` lives in `ui/<feature>/` next to `XScreen` and flows Screen → its caller (NavHost or parent Composable). The ViewModel MUST NOT declare, import, expose, or emit `XAction`. Forbidden constructs on a `ViewModel`: `Channel<*Action>`, `Flow<*Action>`, `SharedFlow<*Action>`, `MutableSharedFlow<*Action>`, `_actions` / `actions` properties of any of these shapes, or a `sealed interface *Action` declared in `viewmodel/`. One-shot side effects originating in VM logic flow back as `state` changes that the Screen reacts to via `LaunchedEffect`, then the Screen — not the VM — calls `onAction(...)`. Violations are merge-blocking (architect check **C12**).
- ViewModel DI lives **in the viewmodel layer** (`<base>.viewmodel.di` for small/medium, `:viewmodel` module for large). Never put `viewModel { }` Koin bindings, `@HiltViewModel` annotations + helper modules, Dagger `ViewModelKey` multibindings, or `ViewModelProvider.Factory` definitions in `data/di` or `:app`. The data layer never depends on the viewmodel layer; viewmodel-DI imports repository/connector interfaces from `domain` and binds the viewmodel constructor-injected with them.
- Screens are stateless about navigation: navigation/help/external nav is emitted through `onAction(XAction)`, never invoked inside the composable.
- Never generate code that bypasses `aca.json`. If a request conflicts with `aca.json` (e.g. "put viewmodel in data module"), stop and ask the user whether to update `aca.json` first.

## Output format when done

Report:
- `aca.json` state (created / read / updated, with the resolved values).
- Files created or modified, grouped by layer.
- DI changes.
- Compile result.
- Anything skipped and why.
