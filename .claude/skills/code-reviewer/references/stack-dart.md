# Dart / Flutter 전용 체크리스트

```
□ build() 안에서 비동기 호출 (build 메서드에서 Future/async 사용)
□ setState 남용 (Riverpod/Bloc 대신 StatefulWidget 과다 사용)
□ const 미사용 (불변 위젯에 const 생성자 미적용)
□ 위젯 트리 과도 중첩 (build() 100줄+, 위젯 추출 필요)
```

| 심각도 | 항목 | 설명 |
|--------|------|------|
| 🟡 | build() 안에서 비동기 호출 | build 메서드에서 Future/async 사용 |
| 🟡 | setState 남용 | Riverpod/Bloc 대신 StatefulWidget 과다 사용 |
| 🟡 | const 미사용 | 불변 위젯에 const 생성자 미적용 |
| 🟡 | 위젯 트리 과도 중첩 | build() 100줄+, 위젯 추출 필요 |

### 🟡 build() 안에서 비동기 호출

```dart
// ❌ build에서 Future 직접 호출 — 매 리빌드마다 재호출, 무한 루프 가능
@override
Widget build(BuildContext context) {
  fetchUserData();  // 비동기 함수 직접 호출
  return FutureBuilder(
    future: getUserFromApi(),  // 매 build마다 새 Future 생성
    builder: (context, snapshot) => Text(snapshot.data ?? ''),
  );
}

// ✅ initState 또는 ref.watch로 단 한 번 호출
class UserScreen extends StatefulWidget { ... }

class _UserScreenState extends State<UserScreen> {
  late Future<User> _userFuture;

  @override
  void initState() {
    super.initState();
    _userFuture = getUserFromApi();  // 한 번만 호출
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder(
      future: _userFuture,  // 안정적인 Future 참조
      builder: (context, snapshot) => Text(snapshot.data?.name ?? ''),
    );
  }
}

// ✅ Riverpod 사용 시 — FutureProvider로 캐싱
final userProvider = FutureProvider.autoDispose<User>((ref) => getUserFromApi());

class UserScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userAsync = ref.watch(userProvider);
    return userAsync.when(
      data: (user) => Text(user.name),
      loading: () => const CircularProgressIndicator(),
      error: (e, _) => Text('오류: $e'),
    );
  }
}
```

### 🟡 setState 남용

```dart
// ❌ StatefulWidget + setState로 전역 상태 관리
class CartScreen extends StatefulWidget { ... }

class _CartScreenState extends State<CartScreen> {
  List<CartItem> items = [];
  bool isLoading = false;
  int totalPrice = 0;

  void addItem(CartItem item) {
    setState(() {
      items.add(item);
      totalPrice += item.price;  // setState가 전체 트리 리빌드
    });
  }
}

// ✅ Riverpod StateNotifier로 상태 분리
@riverpod
class CartNotifier extends _$CartNotifier {
  @override
  CartState build() => CartState.empty();

  void addItem(CartItem item) {
    state = state.copyWith(
      items: [...state.items, item],
      totalPrice: state.totalPrice + item.price,
    );
  }
}

class CartScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cart = ref.watch(cartNotifierProvider);
    return ListView(children: cart.items.map((e) => CartItemTile(item: e)).toList());
  }
}
```

### 🟡 const 미사용

```dart
// ❌ 불변 위젯에 const 없음 — 매 리빌드마다 새 인스턴스 생성
Widget build(BuildContext context) {
  return Column(
    children: [
      Text('제목', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
      SizedBox(height: 16),
      Icon(Icons.star, color: Colors.amber),
    ],
  );
}

// ✅ const 생성자 적용 — 위젯 재사용으로 성능 향상
Widget build(BuildContext context) {
  return const Column(
    children: [
      Text('제목', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
      SizedBox(height: 16),
      Icon(Icons.star, color: Colors.amber),
    ],
  );
}

// ✅ 분리된 위젯에도 const 적용
class TitleText extends StatelessWidget {
  const TitleText({super.key});  // const 생성자

  @override
  Widget build(BuildContext context) {
    return const Text('제목', style: TextStyle(fontSize: 24));
  }
}
```

### 🟡 위젯 트리 과도 중첩

```dart
// ❌ build() 100줄 이상 — 가독성 저하, 재사용 불가
@override
Widget build(BuildContext context) {
  return Scaffold(
    body: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              CircleAvatar(/* 프로필 이미지 */, radius: 40, ...),
              Column(
                children: [
                  Text(user.name, style: /* ... */),
                  Text(user.email, style: /* ... */),
                  // ... 30줄 더 이어짐
                ],
              ),
            ],
          ),
          // ... 70줄 더 이어짐
        ],
      ),
    ),
  );
}

// ✅ 역할별 위젯으로 추출
@override
Widget build(BuildContext context) {
  return Scaffold(
    body: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          _UserProfileHeader(user: user),  // 추출된 위젯
          _UserActivitySection(userId: user.id),
          _UserSettingsSection(settings: user.settings),
        ],
      ),
    ),
  );
}

class _UserProfileHeader extends StatelessWidget {
  const _UserProfileHeader({required this.user});
  final User user;

  @override
  Widget build(BuildContext context) { /* 헤더 전용 로직 */ }
}
```
