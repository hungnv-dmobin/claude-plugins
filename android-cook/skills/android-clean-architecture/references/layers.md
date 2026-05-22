# CA Layers — placement matrix

Resolve every artifact's target path from `aca.json.scope` + the layer it belongs to. Package root below is `<base>` where `<base>` = the project's app namespace (e.g. `com.example.app`).

## Scope: `small` — single `app` module

Everything inside `app/src/main/java/<base>/`:

```
<base>/
├── domain/
│   ├── model/                  # pure kotlin data classes
│   ├── repository/             # concrete repositories (depend on datasource interfaces)
│   ├── connector/              # connector interfaces (VpnConnector, AccessibilityConnector, LiveWallpaperConnector, …)
│   └── datasource/
│       ├── remote/             # remote datasource interfaces
│       └── local/              # local datasource interfaces
├── data/
│   ├── firestore/              # FirestoreXDataSource, FirestoreExtensions
│   ├── room/
│   │   ├── database/           # XRoomDatabase
│   │   ├── entity/             # XEntity
│   │   ├── dao/                # XDao + mapper
│   │   └── impl/               # RoomXDataSource
│   ├── retrofit/
│   │   ├── dto/                # XDto + mapper
│   │   ├── api/                # XApi
│   │   └── impl/               # RetrofitXDataSource
│   ├── datastore/              # DataStoreXDataSource
│   └── di/                     # DI bindings for repositories + datasource impls
├── vpn_connector/              # one package per platform integration (sibling of data)
│   ├── AppVpnService           # platform component (VpnService here; can be Service / BroadcastReceiver / AppWidgetProvider / AccessibilityService / TileService / NotificationListenerService / WallpaperService / overlay window holder)
│   ├── VpnConnectorImp         # concrete VpnConnector
│   └── VpnConnectorModule      # DI bindings for this connector
├── widget_connector/           # additional connectors live as siblings — one package each
│   ├── ThemeWidgetProvider
│   ├── ClockWidgetProvider
│   ├── WidgetConnectorImp
│   └── WidgetConnectorModule
├── viewmodel/
│   ├── <feature>/              # XState, XEvent, XViewModel
│   └── di/                     # ViewModel DI: viewModel{} modules / @HiltViewModel registrations / multibindings / ViewModelFactory — owned by the viewmodel layer, NOT data/di
└── ui/
    └── <feature>/              # XScreen + XAction
```

If `mergeViewModelAndScreen=true`, replace `viewmodel/<feature>` and `ui/<feature>` with a single `feature/<feature>/` package containing all five files (state, event, viewmodel, screen, action). The viewmodel-DI module then lives at `feature/di/` (still owned by the viewmodel half, never `data/di`).

## Scope: `medium` — `core` + `app`

`core` module (Android library, Kotlin-heavy):
```
core/src/main/java/<base>/core/
├── domain/   (model / repository / connector / datasource as above)
└── data/     (firestore / room / retrofit / datastore / di)
```

`app` module:
```
app/src/main/java/<base>/
├── <x>_connector/              # one package per connector (vpn_connector, widget_connector, …)
├── viewmodel/
│   ├── <feature>/
│   └── di/                     # ViewModel DI lives here, NOT in core/data/di
└── ui/<feature>/
```

Connector interfaces always sit in `core` (`<base>.core.domain.connector`). Concrete connector implementations and their platform components (services, receivers, providers, accessibility services, live wallpaper services, overlay holders, etc.) always live in `app` — one package per connector under `app/src/main/java/<base>/<x>_connector/` — so manifest entries stay co-located with the components.

`mergeViewModelAndScreen=true` → `app/src/main/java/<base>/feature/<feature>/`.

## Scope: `large` — module per layer (default)

Modules: `:domain`, `:data`, **one `:<x>-connector` module per platform integration** (e.g. `:vpn-connector`, `:widget-connector`, `:accessibility-connector`, `:live-wallpaper-connector`, `:overlay-connector`, `:notification-connector`), `:viewmodel`, `:ui`, plus `:app` wiring everything.

```
domain/src/main/java/<base>/domain/
├── model/
├── repository/
├── connector/                  # connector interfaces (VpnConnector, WidgetConnector, …)
└── datasource/{remote,local}/

data/src/main/java/<base>/data/
├── firestore/
├── room/{database,entity,dao,impl}/
├── retrofit/{dto,api,impl}/
├── datastore/
└── di/

vpn-connector/src/main/java/<base>/vpn_connector/
├── AppVpnService               # platform component(s)
├── VpnConnectorImp             # concrete connector
└── VpnConnectorModule          # DI bindings
(+ AndroidManifest.xml registering the <service>/<receiver>/<provider> as required)

widget-connector/src/main/java/<base>/widget_connector/
├── ThemeWidgetProvider
├── ClockWidgetProvider
├── WidgetConnectorImp
└── WidgetConnectorModule

viewmodel/src/main/java/<base>/viewmodel/
├── <feature>/
└── di/                         # ViewModel DI module(s) live INSIDE :viewmodel — never :app, never :data
ui/src/main/java/<base>/ui/<feature>/
```

`mergeViewModelAndScreen` is ignored (forced `false`) for `large`.

`:domain` Gradle config: `kotlin("jvm")` or pure Android library with no Android UI deps. Must not depend on `:data`, any `:<x>-connector`, `:viewmodel`, `:ui`.
`:data` depends on `:domain` only.
`:<x>-connector` depends on `:domain` only — **never** on `:data` or another `:<y>-connector`. They are siblings.
`:viewmodel` depends on `:domain` (and `androidx.lifecycle.viewmodel`).
`:ui` depends on `:viewmodel` and `:domain`.
`:app` depends on all of them (`:domain`, `:data`, every `:<x>-connector`, `:viewmodel`, `:ui`) and wires DI + manifest merging.

When scaffolding a new connector module under `large` scope, delegate to the `create-android-module` skill (`--skip-verify`) — same as `:data`. Naming: `<x>-connector` (kebab-case).

## Module dependency rule (all scopes)

```
ui → viewmodel → domain ← data
                       ↑
                  <x>-connector(s)   (one or more, all siblings of data)
```

`ui` never imports `data` or any `<x>-connector` (it goes through viewmodel). `viewmodel` never imports `data` or platform connector implementations — it depends on the **connector interfaces in `domain`** the same way it depends on repository classes. `domain` imports nothing from the other layers. Connector modules never depend on `data`, and `data` never depends on a connector.
