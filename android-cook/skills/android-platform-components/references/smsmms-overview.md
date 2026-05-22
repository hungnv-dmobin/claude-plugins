# smsmms — Integration Overview

`klinker41/android-smsmms` is the de-facto open-source library for sending SMS and MMS on Android. Stock `SmsManager` covers single-part SMS only; MMS requires building APN-aware HTTP bodies, talking to the carrier's MMSC, and parsing PDUs — smsmms wraps all of that.

This doc is an **overview** of how to integrate it. It is not a line-by-line API tour — the library's `Transaction` and `Message` classes are the working surface, and their javadoc is the canonical reference.

## When to use it

Use smsmms when the app sends or receives **MMS** (group messages, picture / video / audio attachments, vCard, anything > 160 chars that needs multi-part with subject). For SMS-only apps, stock `SmsManager` is enough and adding smsmms is overkill.

If the app is a Default-SMS-app candidate, smsmms is almost always the right call — MMS support is part of what the system expects from a Default-SMS handler.

## Dependency setup

smsmms ships as a JitPack-backed artifact. The project's `requirements/app-overview.md` `locked_constraints` block pins the **fork commit hash** the project uses — never depend on `master` or a floating tag.

```kotlin
// app/build.gradle.kts
implementation("com.github.<org>:android-smsmms:<commit-hash-from-locked_constraints>")
```

```kotlin
// settings.gradle.kts
dependencyResolutionManagement {
    repositories {
        maven { url = uri("https://jitpack.io") }
    }
}
```

If the locked fork hash is absent, stop and message `software-architect-android` — picking a fork is an architect-level decision, not a platform-dev call.

## Sending a message

The high-level path is `Transaction(context, Settings()).sendNewMessage(message, threadId)`. Build a `Message` with the recipients, body, and (for MMS) any attachments:

```kotlin
val settings = Settings().apply {
    mmsc = "<from APN>"
    proxy = "<from APN, may be empty>"
    port = "<from APN, may be empty>"
    useSystemSending = true // delegate SMS path to SmsManager; smsmms drives MMS
}

val message = Message(body, recipients.toTypedArray()).apply {
    attachments.forEach { addMedia(it.bytes, it.mimeType) } // MMS only
    subject = mmsSubject // optional
}

Transaction(context, settings).sendNewMessage(message, threadId)
```

Important wiring:

- **APN values** come from the carrier. On API 21+ you can read them from `Telephony.Carriers` if you hold `READ_PRIVILEGED_PHONE_STATE` (system app only) — for normal apps, smsmms can auto-detect via `Utils.getApnSettings(context)`, or the user enters them in app settings.
- **Sent / delivered callbacks** arrive as broadcasts. Register a `BroadcastReceiver` for `com.klinker.android.send_message.MMS_SENT`, `…SMS_SENT`, and `…SMS_DELIVERED` (exact action names depend on the fork — verify in the library source).
- **Default-SMS-app gate** — `SmsManager.sendTextMessage` (which smsmms uses under the hood for SMS) silently drops messages from non-default apps on API 19+. Always check `Telephony.Sms.getDefaultSmsPackage(context) == context.packageName` before calling.

## Receiving a message

Receiving SMS and MMS is **not smsmms's job** — it's the platform's. smsmms only writes incoming MMS that arrive via `WAP_PUSH_DELIVER` into the telephony provider; you still wire the receivers yourself. See `default-sms-role.md` for the four `<receiver>` / `<service>` manifest blocks the Default-SMS role requires.

The typical flow is: incoming SMS / MMS broadcast → your receiver → persist via `ContentResolver.insert(content://sms, …)` / let smsmms persist MMS → emit a domain event to the UI layer.

## Gotchas

A short list. Each is one line because the library's history is long and the reference doc isn't the place to re-derive it — verify against the locked fork's source when in doubt.

- **PendingIntent flags on API 31+** — the fork must use `FLAG_IMMUTABLE` on every PendingIntent it constructs. Upstream did not always; project forks usually patch this. If your locked fork hash predates the patch, sends crash with `IllegalArgumentException` on first dispatch on API 31+ — that's the signal to bump the hash (via the project's update workflow, never inside this skill).
- **APN auto-detection** is fragile on dual-SIM devices and on carriers that don't expose APNs to non-system apps. Always have a manual-entry fallback in settings.
- **Long SMS** is auto-split by `SmsManager` if you pass it to `sendMultipartTextMessage` — smsmms handles this when `useSystemSending = true`.
- **Group MMS** behavior differs by carrier: some send a single multi-recipient MMS, others send N individual MMS. Test on the target carrier — there's no library-side fix.
- **Receivers running >5 s** get killed by the system. Hand off the actual persist + parse work to a `Service` or `WorkManager` job (see `services.md`).
- **Read-after-write** — after `sendNewMessage`, the row appears in `content://sms` asynchronously. Register a `ContentObserver` for UI updates; don't poll.

## Hard rules (smsmms-specific)

- **Never** depend on `master` / a floating tag / `latest`. Always the locked commit hash from `app-overview.md`.
- **Never** edit smsmms source in place inside the consumer project. Patches live in the fork; consumer depends on the fork hash.
- **Never** send from a non-Default-SMS app and assume it succeeded — the silent-drop on non-default packages is the #1 "works on my emulator" bug.
- **Never** call `sendNewMessage` on the main thread. The library does I/O (HTTP for MMS, ContentResolver writes for SMS) inline.
- **Never** assume the fork has every upstream feature — forks freeze. Read the locked fork's source before relying on an API surface seen in upstream docs.

## When to bump the fork hash

Outside this skill. If you find a real bug against the locked fork (FLAG_IMMUTABLE patch missing, APN handling broken on a target device, etc.), file the finding and route the bump through the project's update workflow. Hash bumps are reviewed because the library's API surface is unstable across commits.
