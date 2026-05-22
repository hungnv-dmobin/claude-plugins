# DI wiring per `aca.json.di`

Goal for every feature: bind `<Feature>RemoteDataSource`, `<Feature>LocalDataSource`, and the concrete `<Feature>Repository`, then expose `<Feature>ViewModel`.

**Placement rule (all scopes):** repository + datasource bindings belong to the **data layer** (`<base>.data.di` for small/medium, `:data` module's `di/` for large). **ViewModel bindings belong to the viewmodel layer itself** — never the data layer, never `:app`. Concretely:

- `small` → `<base>.viewmodel.di` package (or `<base>.feature.<feature>.di` if `mergeViewModelAndScreen=true`).
- `medium` → `<base>.viewmodel.di` inside the `app` module (viewmodels live in `app` per `references/layers.md`).
- `large` → `<base>.viewmodel.di` inside the `:viewmodel` Gradle module. Add the viewmodel-DI library deps (`koin-androidx-viewmodel`, Hilt + `@HiltViewModel`, Dagger ViewModel multibinding helpers) to `:viewmodel`'s `build.gradle.kts`. `:app` only aggregates modules — it does not declare viewmodel bindings.

Connector bindings live with their own connector module (see "Connector bindings" below). The data layer never imports anything from the viewmodel layer; the viewmodel DI module imports the repository/connector interfaces from `domain` and binds the viewmodel constructor-injected with them.

## Koin (default)

Split into a **data module** (datasources + repository) and a **viewmodel module** (one per feature, in the viewmodel layer):

```kotlin
// data layer — repositories + datasources
package <base>.data.di

import org.koin.dsl.module

val <feature>DataModule = module {
    single<<Feature>RemoteDataSource> { Retrofit<Feature>DataSource(get()) }
    single<<Feature>LocalDataSource> { Room<Feature>DataSource(get()) }
    single { <Feature>Repository(get(), get()) }
}
```

```kotlin
// viewmodel layer — viewmodels only
package <base>.viewmodel.di

import org.koin.androidx.viewmodel.dsl.viewModel
import org.koin.dsl.module
import <base>.viewmodel.<feature>.<Feature>ViewModel

val <feature>ViewModelModule = module {
    viewModel { <Feature>ViewModel(get() /*, get<<X>Connector>() if needed */) }
}
```

Register **both** modules in `Application.onCreate` `startKoin { modules(...) }`. Append, never replace. For `large` scope, `:viewmodel` must declare `implementation("io.insert-koin:koin-androidx-viewmodel:<version>")` so the `viewModel { }` DSL resolves.

## Hilt

Data-layer modules (datasources + repository) live in `<base>.data.di`:

```kotlin
package <base>.data.di

import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class <Feature>DataModule {
    @Binds @Singleton
    abstract fun bindRemote(impl: Retrofit<Feature>DataSource): <Feature>RemoteDataSource

    @Binds @Singleton
    abstract fun bindLocal(impl: Room<Feature>DataSource): <Feature>LocalDataSource
}

@Module
@InstallIn(SingletonComponent::class)
object <Feature>RepositoryModule {
    @Provides @Singleton
    fun provide<Feature>Repository(
        remote: <Feature>RemoteDataSource,
        local: <Feature>LocalDataSource,
    ): <Feature>Repository = <Feature>Repository(remote, local)
}
```

The viewmodel is annotated **inside the viewmodel layer** with `@HiltViewModel` + `@Inject constructor(...)` so its DI declaration sits next to the class itself, not in `data/di`:

```kotlin
package <base>.viewmodel.<feature>

import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import <base>.domain.connector.<X>Connector
import <base>.domain.repository.<Feature>Repository

@HiltViewModel
class <Feature>ViewModel @Inject constructor(
    private val repository: <Feature>Repository,
    private val <x>Connector: <X>Connector,
) : ViewModel() { /* ... */ }
```

If the viewmodel needs feature-scoped `@Provides` (e.g. a `SavedStateHandle`-derived dependency, or a per-feature dispatcher), add a Hilt module at `<base>.viewmodel.<feature>.di.<Feature>ViewModelModule` `@InstallIn(ViewModelComponent::class)` — keep it inside the viewmodel layer. For `large` scope, `:viewmodel` must enable `kapt`/`ksp` + Hilt plugin and add `dagger-hilt-android` so these annotations compile.

## Dagger (no Hilt)

Data-layer module (in `<base>.data.di`):

```kotlin
@Module
abstract class <Feature>DataModule {
    @Binds @Singleton
    abstract fun bindRemote(impl: Retrofit<Feature>DataSource): <Feature>RemoteDataSource

    @Binds @Singleton
    abstract fun bindLocal(impl: Room<Feature>DataSource): <Feature>LocalDataSource

    companion object {
        @Provides @Singleton
        fun provide<Feature>Repository(
            remote: <Feature>RemoteDataSource,
            local: <Feature>LocalDataSource,
        ): <Feature>Repository = <Feature>Repository(remote, local)
    }
}
```

ViewModel multibinding lives **in the viewmodel layer** (`<base>.viewmodel.di`), not `data/di`. Each feature appends one `@IntoMap @ViewModelKey(...) @Binds` entry into a shared `ViewModelModule`:

```kotlin
package <base>.viewmodel.di

import androidx.lifecycle.ViewModel
import dagger.Binds
import dagger.MapKey
import dagger.Module
import dagger.multibindings.IntoMap
import kotlin.reflect.KClass
import <base>.viewmodel.<feature>.<Feature>ViewModel

@MapKey
@Retention(AnnotationRetention.RUNTIME)
annotation class ViewModelKey(val value: KClass<out ViewModel>)

@Module
abstract class ViewModelModule {
    @Binds @IntoMap @ViewModelKey(<Feature>ViewModel::class)
    abstract fun bind<Feature>ViewModel(vm: <Feature>ViewModel): ViewModel
    // append additional @Binds entries per feature
}
```

ViewModels declare `@Inject constructor(...)` next to their class definition (in the viewmodel layer). `AppComponent.modules` lists `<Feature>DataModule::class` (data) **and** `ViewModelModule::class` (viewmodel). The `ViewModelProvider.Factory` that consumes the multibinding map also lives in the viewmodel layer.

## Pure (manual)

Data graph in an `AppContainer` (data layer):

```kotlin
package <base>.data.di

class AppContainer(context: Context) {
    private val db = <Feature>RoomDatabase.build(context)
    private val api = retrofit.create(<Feature>Api::class.java)

    val <feature>Remote: <Feature>RemoteDataSource = Retrofit<Feature>DataSource(api)
    val <feature>Local: <Feature>LocalDataSource = Room<Feature>DataSource(db.<feature>Dao())
    val <feature>Repository = <Feature>Repository(<feature>Remote, <feature>Local)
}
```

ViewModel factories live **in the viewmodel layer** (`<base>.viewmodel.di.ViewModelFactory`), pulling repositories/connectors from `AppContainer`:

```kotlin
package <base>.viewmodel.di

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.viewmodel.CreationExtras
import androidx.lifecycle.SAVED_STATE_REGISTRY_OWNER_KEY
import androidx.savedstate.SavedStateRegistryOwner
import <base>.viewmodel.<feature>.<Feature>ViewModel
import <base>.data.di.AppContainer

class ViewModelFactory(
    private val container: AppContainer,
    private val <x>Connector: <X>Connector,
) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>, extras: CreationExtras): T {
        @Suppress("UNCHECKED_CAST")
        return when (modelClass) {
            <Feature>ViewModel::class.java ->
                <Feature>ViewModel(container.<feature>Repository, <x>Connector) as T
            else -> error("Unknown ViewModel $modelClass")
        }
    }
}
```

The `app` module (or `Application`) instantiates `AppContainer` + `ViewModelFactory` and passes the factory to UI hosts. Add a feature's `when` branch to the factory inside the viewmodel layer when adding a new viewmodel — never in `data/di`.

## Connector bindings

Each connector ships its **own** DI module: `<X>ConnectorModule`. It binds `<X>Connector` (interface in `domain.connector`) → `<X>ConnectorImp` (in the connector's package/module) as an application-scoped singleton — the platform component and viewmodels share the same instance. Module placement: live alongside the impl in `<base>.<x>_connector` (small/medium) or in the `:<x>-connector` module (large). **Never** put connector bindings in `data/di/`.

### Koin

```kotlin
package <base>.<x>_connector

import org.koin.android.ext.koin.androidContext
import org.koin.dsl.module
import <base>.domain.connector.<X>Connector

val <x>ConnectorModule = module {
    single<<X>Connector> { <X>ConnectorImp(androidContext()) }
}
```

The platform component (`App<X>Service`, widget provider, …) reaches the impl via `getKoin().get<<X>Connector>() as <X>ConnectorImp` (cast is safe — single binding) so it can call `publish(...)`. Register `<x>ConnectorModule` in `Application.onCreate` `startKoin { modules(...) }`.

### Hilt

```kotlin
package <base>.<x>_connector

import android.content.Context
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton
import <base>.domain.connector.<X>Connector

@Module
@InstallIn(SingletonComponent::class)
object <X>ConnectorModule {
    @Provides @Singleton
    fun provide<X>ConnectorImp(@ApplicationContext context: Context): <X>ConnectorImp =
        <X>ConnectorImp(context)

    @Provides @Singleton
    fun provide<X>Connector(impl: <X>ConnectorImp): <X>Connector = impl
}
```

(Keep both `@Provides` so the platform component can inject the concrete `<X>ConnectorImp` for `publish(...)` while viewmodels depend on the `<X>Connector` interface. Platform components use `@AndroidEntryPoint` + `@Inject lateinit var`.)

### Dagger (no Hilt)

```kotlin
@Module
object <X>ConnectorModule {
    @Provides @Singleton
    fun provide<X>ConnectorImp(context: Context): <X>ConnectorImp = <X>ConnectorImp(context)

    @Provides @Singleton
    fun provide<X>Connector(impl: <X>ConnectorImp): <X>Connector = impl
}
```

Add `<X>ConnectorModule::class` to `AppComponent.modules`. Expose an `injectInto(service: App<X>Service)` (or appropriate component-member) on the component so the platform component can grab `<X>ConnectorImp` after `super.onCreate()`.

### Pure (manual)

Add the connector to `AppContainer`:

```kotlin
class AppContainer(context: Context) {
    val <x>Connector: <X>ConnectorImp = <X>ConnectorImp(context)
    // viewmodels see it as the interface:
    val <x>ConnectorIface: <X>Connector get() = <x>Connector
}
```

Platform components retrieve it via `(applicationContext as MyApp).container.<x>Connector` to call `publish(...)`.

## Cross-cutting

- Always update DI in the **same change** as the file you generated. A new repository **or connector** without a binding is a bug.
- For `large` scope, ensure the DI module is in the right Gradle module — repository / datasource bindings live in `:data`'s `di` package; connector bindings live in their own `:<x>-connector` module. Both compile only if those modules depend on `:domain`.
- When adding a new datasource flavor (e.g. switching local from Room to DataStore), replace the binding; do not keep two impls bound to the same interface unless the user explicitly asks for a qualifier.
- Connectors are application singletons by default — the platform component (Service / Receiver / Provider) and the viewmodel must share the same instance for state propagation to work. Do not bind a connector in a request-scoped or feature-scoped scope unless the user explicitly opts in.
