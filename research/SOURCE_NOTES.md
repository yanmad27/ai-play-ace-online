# Đọc source ACE Online phục vụ bot farm Windows

## Nguồn và phạm vi

- Kho: https://st0rmy.de/dl/source/
- Tệp: https://st0rmy.de/dl/source/EP_43_Source.7z
- Ngày tải: 2026-11-12
- SHA-256: `0cda83658bb2ff3f0e5120c34c69d9b8e5883ca442ed56dd892a7e2dddcc0df4`
- Giải nén: `research/vendor/ep43/` (không đưa source bên thứ ba vào Git).
- Trang lưu trữ gọi đây là full EP 4.3 source cho VS2013. Chưa xác minh nguồn gốc, giấy phép hoặc độ khớp với server người dùng.
- Có client `ProjectAtum/ProjectAtum.sln` và server `ProjectsServer/GameServer/GameServer.sln`.
- Đã đọc các đoạn bên dưới, chưa đọc toàn bộ source hoặc biên dịch/chạy executable.
- Comment chủ yếu CP949; đọc bằng Python encoding cp949, errors replace.

## Bằng chứng trong mã client

Đường dẫn tính từ `research/vendor/ep43/ProjectAtum/`.

1. `Common/AtumParam.h:1042`: phân biệt B/M/A/I-Gear bằng bitmask; `IS_ST` cũng chỉ I-Gear.
2. `Common/AtumParam.h:2390`: Siege Mode và Air Siege Mode thuộc A-Gear. Các hằng I-Gear ở 2398 gồm Back Move Mach, Turn Around, Silence, Frenzy, Berserker. Chưa xác định được ý nghĩa cụm “Idle sniper GEAR”; không mặc định nó là I-Gear hoặc A-Gear.
3. `DataRenderLib/main/ShuttleChild.cpp:1606,1631`: tick vũ khí chính nhận trạng thái nút trái, vũ khí phụ nhận trạng thái nút phải.
4. `DataRenderLib/main/ShuttleChild.cpp:12771` (`NewCheckTarget`): lấy tọa độ chuột về client, duyệt danh sách mục tiêu vũ khí chính; kiểm tra khoảng cách con trỏ đến tọa độ mục tiêu trên màn hình hoặc picking. Khi có mục tiêu và chưa có order target thì gán order target. Đây là một hàm chọn mục tiêu đã đọc; chưa xác minh mọi đường gọi và cơ chế chọn của vũ khí phụ.
5. `EtcLib/main/WeaponItemInfo.cpp:188` (`TickNormalWeapon`): xử lý đạn, quá nhiệt, thời gian chuẩn bị và nhịp bắn theo thông số item/nhân vật. Giữ nút bắn vẫn chịu các điều kiện này.
6. `EtcLib/main/WeaponItemInfo.cpp:715`: trong nhánh bắn chính đã đọc, tầm bắn được tính từ radar; so khoảng cách 3D với tầm và kiểm tra order target. Không hardcode khoảng cách farm trước khi biết đồ đang dùng.
7. `InterfaceLib/main/INFTarget.cpp:1662`: HUD quái dùng HP hiện tại/max HP và tên quái. `RenderAutoTarget` cũng xử lý tọa độ hiển thị mục tiêu. Có thể dùng HUD này làm tín hiệu thị giác cho bot.

## Hệ quả cho triển khai

Đề xuất bot ngoài game: capture cửa sổ → nhận diện quái/HUD → đưa chuột đến mục tiêu → kiểm tra khóa mục tiêu → bắn theo vũ khí → kiểm tra HP mục tiêu giảm → tìm mục tiêu tiếp theo. Cần xử lý quá nhiệt/hết đạn và hồi phục.

Đây là đề xuất thiết kế từ mã đã đọc, chưa phải bot đã thử nghiệm. Cần đối chiếu client Windows thực tế và xác định đúng gear/chế độ sniper. Không suy ra hotkey Tab chọn quái: vị trí Tab tìm thấy gần dòng 2973 nằm trong comment.
