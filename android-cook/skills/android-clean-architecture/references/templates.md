# Kotlin templates

Replace `<base>`, `<Feature>` (PascalCase), `<feature>` (snake_case) per request. Keep MVI shape exactly as shown.

## Domain — model

```kotlin
package <base>.domain.model

data class <Feature>(
    val id: String,
    // ...domain fields, pure kotlin only
)
```

## Domain — datasource interfaces

```kotlin
// remote
package <base>.domain.datasource.remote

import <base>.domain.model.<Feature>
import kotlinx.coroutines.flow.Flow

interface <Feature>RemoteDataSource {
    suspend fun fetch(id: String): <Feature>
    fun observeAll(): Flow<List<<Feature>>>
    suspend fun upsert(item: <Feature>)
    suspend fun delete(id: String)
}
```

```kotlin
// local
package <base>.domain.datasource.local

import <base>.domain.model.<Feature>
import kotlinx.coroutines.flow.Flow

interface <Feature>LocalDataSource {
    fun observeAll(): Flow<List<<Feature>>>
    suspend fun get(id: String): <Feature>?
    suspend fun upsert(item: <Feature>)
    suspend fun delete(id: String)
}
```

## Domain — repository (concrete)

```kotlin
package <base>.domain.repository

import <base>.domain.datasource.local.<Feature>LocalDataSource
import <base>.domain.datasource.remote.<Feature>RemoteDataSource
import <base>.domain.model.<Feature>
import kotlinx.coroutines.flow.Flow

class <Feature>Repository(
    private val remote: <Feature>RemoteDataSource,
    private val local: <Feature>LocalDataSource,
) {
    fun observeAll(): Flow<List<<Feature>>> = local.observeAll()

    suspend fun refresh(id: String) {
        val fresh = remote.fetch(id)
        local.upsert(fresh)
    }
}
```

## Data — Room

```kotlin
// entity
package <base>.data.room.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "<feature>")
data class <Feature>Entity(
    @PrimaryKey val id: String,
    // ...columns
)
```

```kotlin
// dao + mapper
package <base>.data.room.dao

import androidx.room.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import <base>.data.room.entity.<Feature>Entity
import <base>.domain.model.<Feature>

@Dao
interface <Feature>Dao {
    @Query("SELECT * FROM <feature>") fun observeAll(): Flow<List<<Feature>Entity>>
    @Query("SELECT * FROM <feature> WHERE id = :id") suspend fun get(id: String): <Feature>Entity?
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(item: <Feature>Entity)
    @Query("DELETE FROM <feature> WHERE id = :id") suspend fun delete(id: String)
}

internal fun <Feature>Entity.toDomain(): <Feature> = <Feature>(id = id /*, ...*/)
internal fun <Feature>.toEntity(): <Feature>Entity = <Feature>Entity(id = id /*, ...*/)

fun <Feature>Dao.observeAllDomain(): Flow<List<<Feature>>> =
    observeAll().map { rows -> rows.map { it.toDomain() } }
```

```kotlin
// impl
package <base>.data.room.impl

import <base>.data.room.dao.*
import <base>.domain.datasource.local.<Feature>LocalDataSource
import <base>.domain.model.<Feature>
import kotlinx.coroutines.flow.Flow

class Room<Feature>DataSource(
    private val dao: <Feature>Dao,
) : <Feature>LocalDataSource {
    override fun observeAll(): Flow<List<<Feature>>> = dao.observeAllDomain()
    override suspend fun get(id: String): <Feature>? = dao.get(id)?.toDomain()
    override suspend fun upsert(item: <Feature>) = dao.upsert(item.toEntity())
    override suspend fun delete(id: String) = dao.delete(id)
}
```

## Data — Retrofit

```kotlin
// dto + mapper
package <base>.data.retrofit.dto

import <base>.domain.model.<Feature>

data class <Feature>Dto(val id: String /*, ...*/) {
    fun toDomain(): <Feature> = <Feature>(id = id /*, ...*/)
}
```

```kotlin
// api
package <base>.data.retrofit.api

import retrofit2.http.*
import <base>.data.retrofit.dto.<Feature>Dto

interface <Feature>Api {
    @GET("<feature>/{id}") suspend fun fetch(@Path("id") id: String): <Feature>Dto
}
```

```kotlin
// impl
package <base>.data.retrofit.impl

import <base>.data.retrofit.api.<Feature>Api
import <base>.domain.datasource.remote.<Feature>RemoteDataSource
import <base>.domain.model.<Feature>
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

class Retrofit<Feature>DataSource(
    private val api: <Feature>Api,
) : <Feature>RemoteDataSource {
    override suspend fun fetch(id: String): <Feature> = api.fetch(id).toDomain()
    override fun observeAll(): Flow<List<<Feature>>> = flow { /* implement as needed */ }
    override suspend fun upsert(item: <Feature>) { /* POST/PUT */ }
    override suspend fun delete(id: String) { /* DELETE */ }
}
```

## Data — Firestore

```kotlin
package <base>.data.firestore

import com.google.firebase.firestore.FirebaseFirestore
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import <base>.domain.datasource.remote.<Feature>RemoteDataSource
import <base>.domain.model.<Feature>

class Firestore<Feature>DataSource(
    private val db: FirebaseFirestore,
) : <Feature>RemoteDataSource {
    private val collection get() = db.collection("<feature>")
    override suspend fun fetch(id: String): <Feature> =
        collection.document(id).get().await().toDomain()
    override fun observeAll(): Flow<List<<Feature>>> = callbackFlow {
        val reg = collection.addSnapshotListener { snap, _ ->
            trySend(snap?.documents?.mapNotNull { it.toDomain() } ?: emptyList())
        }
        awaitClose { reg.remove() }
    }
    override suspend fun upsert(item: <Feature>) { collection.document(item.id).set(item.toMap()).await() }
    override suspend fun delete(id: String) { collection.document(id).delete().await() }
}
```

Place shared helpers (`await()`, `DocumentSnapshot.toDomain()`, `<Feature>.toMap()`) in `data/firestore/FirestoreExtensions.kt`. Create that file once, append per feature.

## Data — DataStore

```kotlin
package <base>.data.datastore

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

class DataStore<Feature>DataSource(
    private val store: DataStore<Preferences>,
) : <Feature>LocalDataSource {
    // implement using preferencesKey lookups
}
```

## ViewModel — state / event / viewmodel

```kotlin
package <base>.viewmodel.<feature>

data class <Feature>State(
    val loading: Boolean = true,
    val error: String = "",
    val items: List<<Model>> = emptyList(),
)
```

```kotlin
package <base>.viewmodel.<feature>

sealed interface <Feature>Event {
    data object Refresh : <Feature>Event
    data class Select(val id: String) : <Feature>Event
}
```

```kotlin
package <base>.viewmodel.<feature>

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import <base>.domain.repository.<Feature>Repository

class <Feature>ViewModel(
    private val repository: <Feature>Repository,
) : ViewModel() {

    private val _state = MutableStateFlow(<Feature>State())
    val state = _state.asStateFlow()

    val onEvent: (<Feature>Event) -> Unit = { event ->
        when (event) {
            <Feature>Event.Refresh -> refresh()
            is <Feature>Event.Select -> { /* ... */ }
        }
    }

    init { observe() }

    private fun observe() {
        viewModelScope.launch {
            repository.observeAll().collect { items ->
                _state.update { it.copy(loading = false, items = items) }
            }
        }
    }

    private fun refresh() {
        viewModelScope.launch(CoroutineExceptionHandler { _, t ->
            _state.update { it.copy(error = t.message ?: "error") }
        }) { /* repository.refresh(...) */ }
    }
}
```

## UI — screen + action

```kotlin
package <base>.ui.<feature>

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import <base>.viewmodel.<feature>.<Feature>Event
import <base>.viewmodel.<feature>.<Feature>State

sealed interface <Feature>Action {
    data class Selected(val id: String) : <Feature>Action
    data object GoBack : <Feature>Action
}

@Composable
fun <Feature>Screen(
    modifier: Modifier = Modifier,
    state: <Feature>State = <Feature>State(),
    onEvent: (<Feature>Event) -> Unit = {},
    onAction: (<Feature>Action) -> Unit = {},
) {
    // Scaffold + content. Emit user-driven domain changes via onEvent(...),
    // navigation/external concerns via onAction(...).
}
```

If `mergeViewModelAndScreen=true` and scope ≠ large, place all five files in `<base>.feature.<feature>` instead of split `viewmodel.<feature>` / `ui.<feature>`.

## MVI separation — what goes where (read before copying the templates above)

The split between `Event` and `Action` is **load-bearing**, not stylistic. Get it wrong and the ViewModel grows a `Channel<Action>` that the Screen passes everything through to and the root Composable handles back out — wasted plumbing and a CA violation.

| Concept | Owner | Direction | Examples |
|---|---|---|---|
| `XState` | `viewmodel/<feature>/` | VM → Screen | loading flags, item lists, error strings |
| `XEvent` | `viewmodel/<feature>/` | Screen → VM | "user tapped refresh", "user typed `q`", "permission re-check returned `granted`" |
| `XAction` | `ui/<feature>/` (next to `XScreen`) | Screen → its caller | "navigate back", "open settings intent", "show snackbar", "return result to previous step" |

Rules that fall out of this split:

- **ViewModel never knows that `XAction` exists.** It must not import it, declare it, expose it, or emit it.
- **Action is emitted at the `XScreen` callsite, not from inside the VM.** The Screen calls `onAction(XAction.GoBack)` when the user taps back; the NavHost wires that callback to `navController.popBackStack()`.
- **One-shot side effects that *originate* from VM logic** (e.g. "fire-and-forget intent after a successful refresh") still flow back as state changes (`state.shouldLaunchSettings = true`) the Screen reacts to in a `LaunchedEffect`, then sends an `Event` back to clear the flag. Do **not** introduce `Channel<XAction>` / `SharedFlow<XAction>` / `MutableSharedFlow<XAction>` on the VM to "simulate" one-shot events.

### Forbidden in `<Feature>ViewModel` — copy the rejection reason into the code-review bug if you see this

```kotlin
// WRONG — Action declared in viewmodel package, exposed as Flow from VM
sealed interface DeniedRecoveryAction { /* ... */ }       // belongs in ui/<feature>/, not here

class DeniedRecoveryViewModel : ViewModel() {
    private val _actions = Channel<DeniedRecoveryAction>(Channel.BUFFERED)   // WRONG
    val actions = _actions.receiveAsFlow()                                    // WRONG

    fun onEvent(e: DeniedRecoveryEvent) {
        viewModelScope.launch { _actions.send(DeniedRecoveryAction.LaunchSettings(...)) }   // WRONG
    }
}
```

Why it's wrong: the VM is dictating navigation/external concerns it has no business owning. The Screen ends up as a pass-through — receiving an `Event` from the user, forwarding to VM, VM re-emits as `Action`, root collects from `vm.actions` and calls `onAction(...)`. Three hops for one user tap.

### Correct shape

```kotlin
// viewmodel/<feature>/DeniedRecoveryViewModel.kt — no Action, ever
class DeniedRecoveryViewModel(reason: DeniedReason) : ViewModel() {
    private val _state = MutableStateFlow(DeniedRecoveryState(reason = reason))
    val state = _state.asStateFlow()

    val onEvent: (DeniedRecoveryEvent) -> Unit = { event ->
        when (event) {
            DeniedRecoveryEvent.ReGrantClicked -> _state.update { it.copy(launchSettings = true) }
            DeniedRecoveryEvent.SkipClicked    -> _state.update { it.copy(skipRequested = true) }
            is DeniedRecoveryEvent.SettingsIntentResult ->
                _state.update { it.copy(intentError = !event.resolved, launchSettings = false) }
            is DeniedRecoveryEvent.PermissionRechecked ->
                if (event.granted) _state.update { it.copy(returnToOrigin = true) }
        }
    }
}
```

```kotlin
// ui/<feature>/DeniedRecoveryScreen.kt — Action lives here, emitted at this callsite
sealed interface DeniedRecoveryAction {
    data class LaunchSettings(val reason: DeniedReason) : DeniedRecoveryAction
    data object ReturnToPreviousStep : DeniedRecoveryAction
    data class ReturnToOrigin(val reason: DeniedReason) : DeniedRecoveryAction
}

@Composable
fun DeniedRecoveryScreen(
    state: DeniedRecoveryState,
    onEvent: (DeniedRecoveryEvent) -> Unit,
    onAction: (DeniedRecoveryAction) -> Unit,
) {
    LaunchedEffect(state.launchSettings) {
        if (state.launchSettings) onAction(DeniedRecoveryAction.LaunchSettings(state.reason))
    }
    LaunchedEffect(state.skipRequested) {
        if (state.skipRequested) onAction(DeniedRecoveryAction.ReturnToPreviousStep)
    }
    LaunchedEffect(state.returnToOrigin) {
        if (state.returnToOrigin) onAction(DeniedRecoveryAction.ReturnToOrigin(state.reason))
    }
    // ...content...
}
```

The NavHost (or parent screen) supplies `onAction = { action -> when (action) { ... navController.navigate(...) } }`. The VM never imports `DeniedRecoveryAction`.

## Connector

Connectors bridge viewmodels to Android platform providers (services, broadcast receivers, overlay views, widget providers, accessibility services, vpn services, notification listeners, live wallpaper services). One package/module per connector. Connectors are siblings of `data` — they do **not** import a repository, and `data` does not import a connector. ViewModels inject connector interfaces directly.

`<X>` below = the connector subject in PascalCase (e.g. `Vpn`, `Widget`, `Accessibility`, `LiveWallpaper`, `Overlay`, `Notification`). `<x>` = snake_case (`vpn`, `widget`, `live_wallpaper`).

### Connector — interface (in `domain/connector/`)

The interface is pure Kotlin — no Android imports. Expose **commands** (suspend functions or fire-and-forget) and **observable platform state** (`Flow`).

```kotlin
package <base>.domain.connector

import <base>.domain.model.<X>ConnectionInfo
import <base>.domain.model.<X>ConnectionConfig
import <base>.domain.model.<X>ConnectionStatus
import <base>.domain.model.<X>PermissionState
import kotlinx.coroutines.flow.Flow

interface <X>Connector {
    val connectionInfo: Flow<<X>ConnectionInfo>
    fun checkPermission(): <X>PermissionState
    suspend fun connect(config: <X>ConnectionConfig): <X>ConnectionStatus
    suspend fun disconnect(): Boolean
}
```

Models referenced (`<X>ConnectionInfo`, `<X>ConnectionConfig`, `<X>ConnectionStatus`, `<X>PermissionState`) live in `domain/model/` as pure Kotlin types. Generate them alongside the connector interface.

### Connector — platform component(s)

Pick the platform class matching the integration. Common shapes:

```kotlin
// VPN service
package <base>.<x>_connector

import android.content.Intent
import android.net.VpnService

class App<X>Service : VpnService() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // build VPN tunnel based on intent extras; push status updates to <X>ConnectorImp.
        return START_STICKY
    }
}
```

```kotlin
// Widget provider
package <base>.<x>_connector

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context

class Theme<X>Provider : AppWidgetProvider() {
    override fun onUpdate(context: Context, mgr: AppWidgetManager, ids: IntArray) {
        // render RemoteViews, request <X>ConnectorImp for current data via app-scoped lookup.
    }
}
```

Other shapes (use the corresponding base class; same package): `BroadcastReceiver`, `AccessibilityService`, `WallpaperService`, `NotificationListenerService`, `Service` (foreground / bound), or a Kotlin object owning a `WindowManager` overlay.

Register every component in the connector module's `AndroidManifest.xml`:

```xml
<service
    android:name="<base>.<x>_connector.App<X>Service"
    android:permission="android.permission.BIND_VPN_SERVICE"
    android:exported="false">
    <intent-filter>
        <action android:name="android.net.VpnService"/>
    </intent-filter>
</service>
```

(Adjust `<service>` / `<receiver>` / `<provider>` and `intent-filter` / `permission` per platform integration.)

### Connector — implementation (`<X>ConnectorImp`)

Owns a hot state holder (`MutableStateFlow`) the platform component pushes into, and translates suspend commands into `Context.startService` / `Intent` / `WindowManager.addView` / etc.

```kotlin
package <base>.<x>_connector

import android.content.Context
import android.content.Intent
import <base>.domain.connector.<X>Connector
import <base>.domain.model.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

class <X>ConnectorImp(
    private val context: Context,
) : <X>Connector {

    private val _connectionInfo = MutableStateFlow(<X>ConnectionInfo.Disconnected)
    override val connectionInfo: Flow<<X>ConnectionInfo> = _connectionInfo.asStateFlow()

    override fun checkPermission(): <X>PermissionState {
        // probe permission API for this platform (VpnService.prepare, AccessibilityManager, …)
        TODO()
    }

    override suspend fun connect(config: <X>ConnectionConfig): <X>ConnectionStatus {
        val intent = Intent(context, App<X>Service::class.java).apply {
            // pack config into extras
        }
        context.startService(intent)
        return <X>ConnectionStatus.Connecting
    }

    override suspend fun disconnect(): Boolean {
        context.stopService(Intent(context, App<X>Service::class.java))
        return true
    }

    // Called by App<X>Service when platform state changes.
    internal fun publish(info: <X>ConnectionInfo) { _connectionInfo.value = info }
}
```

The platform component reaches `<X>ConnectorImp.publish(...)` via the DI container (Hilt entry point, Koin `getKoin().get()`, or an `Application`-scoped singleton for `pure`). Never expose mutable state outside the impl.

### Connector — DI module (`<X>ConnectorModule`)

See `references/di.md` → "Connector bindings" for per-DI-library snippets. Always bind `<X>Connector` → `<X>ConnectorImp` as an application singleton, since platform components and viewmodels share the same instance.

### ViewModel using a connector

ViewModels inject connector interfaces alongside repositories. Same MVI shape — events that touch the platform call `viewModelScope.launch { connector.connect(...) }`; observable state collects from `connector.connectionInfo`.

```kotlin
class <Feature>ViewModel(
    private val repository: <Feature>Repository,
    private val <x>Connector: <X>Connector,
) : ViewModel() {
    init {
        viewModelScope.launch {
            <x>Connector.connectionInfo.collect { info ->
                _state.update { it.copy(<x>Info = info) }
            }
        }
    }
}
```
