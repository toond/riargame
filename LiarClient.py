from socket import *
from tkinter import *
from threading import Thread
import threading
from tkinter.scrolledtext import ScrolledText
from queue import Queue

class LiarGameClient:
    def __init__(self, server_host='127.0.0.1', server_port=2505):
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect((server_host, server_port))

        # self.name = input("사용자 이름을 입력하세요: ")
        # self.client_socket.sendall(self.name.encode('utf-8'))  # 이름을 서버에 전달

        self.listen_thread = Thread(target=self.receive_messages, daemon=True)
        self.listen_thread.start()

        self.chat_transcript_area = None
        self.user_activity_area = None

        self.message_queue = Queue()  # UI 업데이트를 위한 메시지 큐

        self.root = Tk()  # Initialize root window here
        self.init_main_screen()

    def init_main_screen(self):
        self.root.title("라이어 게임 클라이언트")
        self.root.geometry("400x300")

        Label(self.root, text="라이어 게임", font=("Arial", 20)).pack(pady=20)

        Button(self.root, text="방 만들기", command=self.create_room_ui, width=15, height=2).pack(pady=20)
        Button(self.root, text="방 참여하기", command=self.join_room_ui, width=15, height=2).pack(pady=20)

        # UI 업데이트를 위한 메인 루프에서 큐를 체크
        self.root.after(100, self.process_message_queue)
        self.root.mainloop()

    def process_message_queue(self):
        while not self.message_queue.empty():
            message = self.message_queue.get_nowait()
            self.update_user_activity_safe(message)
        self.root.after(1000, self.process_message_queue)

    def create_room_ui(self):
        self.clear_window()

        Label(self.root, text="방 만들기", font=("Arial", 16)).pack(pady=10)

        frame = Frame(self.root)
        frame.pack(pady=5, anchor="center")

        Label(frame, text="방 ID:").pack(side="left", padx=(5, 5))
        room_id_entry = Entry(frame)
        room_id_entry.pack(side="left")

        frame2 = Frame(self.root)
        frame2.pack(pady=5, anchor="center")
        Label(frame2, text="사용자 이름:").pack(side="left", padx=(5, 5))
        name_entry = Entry(frame2)
        name_entry.pack(side="left")

        def create_room():
            room_id = room_id_entry.get()
            name = name_entry.get()
            if not room_id:
                Label(self.root, text="방 ID를 입력해주세요.", fg="red").pack(pady=5)
                return

            self.send_message(f"CREATE_ROOM {room_id} {name}")
            response = self.client_socket.recv(256).decode('utf-8')

            if response == "ROOM_CREATED":
                self.root.after(0, self.show_room_ui, room_id)
            else:
                Label(self.root, text="방 생성에 실패했습니다. (중복된 방 ID)", fg="red").pack(pady=5)

        Button(self.root, text="방 만들기", command=create_room, width=15, height=2).pack(pady=20)
        Button(self.root, text="뒤로가기", command=lambda: self.clear_window() or self.init_main_screen(), width=15, height=2).pack(pady=10)

    def join_room_ui(self):
        self.clear_window()

        Label(self.root, text="방 참여하기", font=("Arial", 16)).pack(pady=10)

        frame = Frame(self.root)
        frame.pack(pady=5, anchor="center")

        Label(frame, text="방 ID:").pack(side="left", padx=(5, 5))
        room_id_entry = Entry(frame)
        room_id_entry.pack(side="left")

        frame2 = Frame(self.root)
        frame2.pack(pady=5, anchor="center")
        Label(frame2, text="사용자 이름:").pack(side="left", padx=(5, 5))
        name_entry = Entry(frame2)
        name_entry.pack(side="left")

        def join_room():
            room_id = room_id_entry.get()
            name = name_entry.get()
            if not room_id:
                Label(self.root, text="방 ID를 입력해주세요.", fg="red").pack(pady=5)
                return

            threading.Thread(target=self._join_room_thread, args=(room_id, name,), daemon=True).start()

        Button(self.root, text="방 참여하기", command=join_room, width=10, height=1).pack(pady=10)
        Button(self.root, text="뒤로가기", command=lambda: self.clear_window() or self.init_main_screen(), width=10, height=1).pack(pady=10)

    def _join_room_thread(self, room_id, name):
        try:
            self.send_message(f"JOIN_ROOM {room_id} {name}")
            response = self.client_socket.recv(256).decode('utf-8')

            if response == "ROOM_JOIN":
                self.root.after(0, self.show_room_ui, room_id)
            else:
                self.message_queue.put("방이 가득 찼거나 존재하지 않습니다.")
        except Exception as e:
            self.message_queue.put(f"오류 발생: {e}")

    def show_room_ui(self, room_id):
        self.clear_window()
        self.root.geometry("700x600")

        Label(self.root, text=f"방 ID: {room_id}", font=("Arial", 16)).pack(pady=10)

        chat_frame = Frame(self.root)
        chat_frame.pack(pady=5, fill=BOTH, expand=True)

        self.user_activity_area = ScrolledText(chat_frame, height=20, width=80, state="disabled")
        self.user_activity_area.pack(side=LEFT, fill=BOTH, expand=True, padx=5, pady=5)

        input_frame = Frame(self.root)
        input_frame.pack(pady=5)

        input_field = Entry(input_frame, width=40)
        input_field.pack(side=LEFT, padx=5)

        def send_message1():
            message = input_field.get()
            print("설명" + message)
            input_field.delete(0, 'end')
            self.send_message(f"EXPLAIN {room_id} {message}")
        def send_message2():
            message = input_field.get()
            print("투표" + message)
            input_field.delete(0, 'end')
            self.send_message(f"VOTE {room_id} {message}")
        def send_message3():
            message = input_field.get()
            print("답변" + message)
            input_field.delete(0, 'end')
            self.send_message(f"ANSWER {room_id} {message}")

        Button(input_frame, text="보내기", command=send_message1, width=10, height=1).pack(side=LEFT)
        Button(input_frame, text="투표하기", command=send_message2, width=10, height=1).pack(side=LEFT)
        Button(input_frame, text="답변하기", command=send_message3, width=10, height=1).pack(side=LEFT)

        exit_frame = Frame(self.root)
        exit_frame.pack(pady=10)
        Button(exit_frame, text="퇴장", command=lambda: self.exit_room(room_id), width=10, height=1).pack()

    def exit_room(self, room_id):
        self.send_message(f"EXIT_ROOM {room_id}")
        self.clear_window()
        self.init_main_screen()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def send_message(self, message):
        # 메시지를 별도의 스레드에서 보내도록 수정
        threading.Thread(target=self._send_message_thread, args=(message,), daemon=True).start()

    def _send_message_thread(self, message):
        try:
            self.client_socket.sendall(message.encode('utf-8'))
        except Exception as e:
            self.message_queue.put(f"메시지 전송 오류: {e}")

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message.startswith("EXIT_TO_MAIN"):
                    # 현재 화면의 모든 위젯 삭제
                    for widget in self.root.winfo_children():
                        widget.destroy()
                    self.init_main_screen()  # 메인 화면 초기화 메서드 호출
                if message:
                    self.message_queue.put(message)
            except Exception as e:
                self.message_queue.put(f"수신 오류: {e}")
                break

    def update_user_activity_safe(self, message):
        try:
            # 위젯이 아직 존재하는지 확인
            if self.user_activity_area.winfo_exists():
                self.user_activity_area.configure(state="normal")
                self.user_activity_area.insert('end', message + '\n')
                self.user_activity_area.configure(state="disabled")
        except Exception as e:
            print(f"Error updating user activity: {e}")

if __name__ == "__main__":
    host = '127.0.0.1'
    port = 2505
    LiarGameClient(host, port)
