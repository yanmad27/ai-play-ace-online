# ACE Pilot — Windows I-Gear learning prototype

Phát triển trên macOS, build Windows x64 bằng GitHub Actions + PyInstaller.

## Trạng thái thực tế

Đã có ứng dụng ghi hình cửa sổ và trạng thái điều khiển ở 10 Hz, huấn luyện mô hình bắt chước nhẹ trên CPU, quan sát dự đoán, kích hoạt mô hình và điều khiển thử. Đây là baseline thử đường dữ liệu, **chưa phải AI farm thành thạo**, chưa có detector quái riêng, nhận biết chết/hồi máu hoặc tự học bằng reward. Mô hình ảnh xám nhỏ có thể bỏ sót quái xa; chưa chứng minh phù hợp để bay chiến đấu. Chưa thử trong client thật.

## Build Windows

Đẩy repository này lên GitHub, mở **Actions → Build Windows → Run workflow** (push main cũng tự build). Khi thành công, tải artifact **AcePilot-Windows-x64**, giải nén toàn bộ rồi mở `AcePilot.exe`. Không cần Python trên máy chơi. Giữ cửa sổ console để xem lỗi khởi động.

Workflow chạy unit tests, smoke test Win32, build và smoke test trực tiếp exe. GitHub hosted runner chỉ kiểm tra ứng dụng/build; không có game để kiểm chứng farm.

## Sử dụng

1. Chạy game ở windowed/borderless, cố định kích thước cửa sổ và cấu hình phím. Điền **đúng toàn bộ tiêu đề cửa sổ** vào app.
2. Bấm **Record demonstration**, trong 5 giây chuyển focus sang game rồi chơi. F8 dừng và lưu. Mỗi phiên tối đa 5 phút. Ghi ít nhất hai phiên riêng cùng bãi farm; phiên cuối dành riêng cho đánh giá.
3. Bấm **Train candidate** khi nghỉ chơi. Dữ liệu nằm ở `%LOCALAPPDATA%\AcePilot`, gồm video MJPEG, mẫu học, metadata và `validation.json`.
4. Chạy **Observe candidate**: chưa phát input; dự đoán được lưu ở thư mục `predictions/` dưới dạng JSONL (hai giá trị đầu là tọa độ chuột chuẩn hóa, tiếp theo là trạng thái controls theo metadata). Đánh giá offline không đảm bảo farm tốt.
5. **Activate candidate** rồi **Run active model** để thử có giám sát. F8 dừng; mất focus hoặc đổi kích thước cũng dừng. Các nút bot giữ sẽ được thả. Muốn dạy sửa sai: F8 → Record demonstration → thao tác sửa → train lại. Hiện chưa có chuyển tiếp sửa sai liền mạch.

Mô hình học vị trí chuột tương đối với client và trạng thái W/A/S/D/Space/1–5/chuột trái/phải. Chưa ghi mọi phím, thao tác cuộn hoặc relative mouse delta. Nếu game khóa/ẩn con trỏ hoặc không nhận Win32 synthetic input thì bộ điều khiển này cần thay adapter. Không có cam kết tương thích mọi client.

Không tự kích hoạt model mới. Bản trước được giữ ở `previous.joblib`. Chỉ mở model do app của bạn tạo vì joblib là định dạng thực thi khi nạp.

## Phát triển trên Mac

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python run.py --self-test
```

Cửa sổ ghi/điều khiển chỉ chạy Windows. Dữ liệu video gốc được giữ để sau này bổ sung detector và mô hình chuỗi ảnh tốt hơn mà không phải ghi lại từ đầu. `research/SOURCE_NOTES.md` ghi các đoạn source game đã khảo sát.
