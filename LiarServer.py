from socket import *
from threading import Thread
import random
import time

class LiarGameServer:
    def __init__(self, host='127.0.0.1', port=2505):
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.server_socket.listen(10)
        print("서버가 시작되었습니다. 클라이언트를 기다립니다...")

        self.clients = {}
        self.rooms = {}  # 방 목록
        self.answers = {
            "국가": ["한국", "미국", "일본", "중국"],
            "동물": ["고양이", "강아지", "코끼리", "기린"],
            "식물": ["장미", "선인장", "소나무", "벚꽃"],
            "직업": ["의사", "교사", "개발자", "경찰"]
        }

        self.start_game()

    def broadcast(self, message, room_id):
        for client in self.rooms[room_id]['players']:
            try:
                # 메시지에 {name}이 있을 경우 이름으로 대체
                if "{name}" in message:
                    player_name = self.clients.get(client, "Unknown Player")  # 이름 가져오기
                    message = message.replace("{name}", player_name)
                client.sendall(message.encode('utf-8'))
            except Exception as e:
                print(f"Error sending message to client {client}: {e}")

    def send_to_client(self, client, message):
        client.sendall(message.encode('utf-8'))

    def handle_client(self, client, addr):
        # name = client.recv(256).decode('utf-8')  # 클라이언트로부터 이름 받기
        # print(f"{name}님이 접속했습니다. ({addr})")
        # # 클라이언트 이름과 소켓을 딕셔너리에 저장
        # self.clients[client] = name

        # 방 생성 및 참여 로직 처리
        while True:
            message = client.recv(256).decode('utf-8')
            print("클라이언트가 보낸 설명 : " + message)
            if message.startswith("CREATE_ROOM"):
                room_id = message.split()[1]
                name = message.split()[2]
                self.clients[client] = name
                if room_id not in self.rooms:  # 방이 존재하지 않으면 방을 생성
                    self.rooms[room_id] = {'players': [client], 'leader': name, 'game_started': False}
                    self.broadcast(f"{name}님이 방을 만들었습니다. 방에 참여할 수 있습니다.", room_id)
                    self.send_to_client(client, "ROOM_CREATED")
                else:
                    self.send_to_client(client, "ROOM_EXISTS")

            elif message.startswith("JOIN_ROOM"):
                room_id = message.split()[1]
                name = message.split()[2]
                self.clients[client] = name
                print(f"{name}님이 접속했습니다. ({addr})")
                if room_id in self.rooms and len(self.rooms[room_id]['players']) < 4:
                    self.rooms[room_id]['players'].append(client)
                    self.broadcast(f"{name}님이 방에 참여했습니다.", room_id)
                    self.send_to_client(client, "ROOM_JOIN")

                    if len(self.rooms[room_id]['players']) == 3:
                        self.start_game_in_room(room_id)
                else:
                    self.send_to_client(client, "ROOM_FULL_OR_NOT_FOUND")
            elif message.startswith("EXPLAIN"):
                parts = message.split(' ', 2)
                if len(parts) == 3:
                    _, room_id, msg = parts
                    print(f"Room ID: {room_id}, Message: {msg}")
                    self.handle_explanation(client, room_id, msg)
                else:
                    print(f"잘못된 메시지 형식: {message}")  # 메시지가 잘못된 형식일 때 출력
            elif message.startswith("VOTE"):
                _, room_id, vote = message.split(' ', 2)
                room_id = room_id
                print(f"Room ID: {room_id}, Message: {vote}")
                # 투표 함수에 room_id랑 vote(투표당한사람이름) 넘겨줘서 처리
                # 메시지 분리: "VOTE room_id vote" 형태
                _, room_id, vote = message.split(' ', 2)
                room_id = room_id # room_id는 정수로 변환

                # 해당 방 정보 가져오기
                room = self.rooms[room_id]
                vote_count = room.get('vote_count', {})  # 투표 카운트를 저장할 딕셔너리 (없으면 빈 딕셔너리로 초기화)
                count = room.get('vote_count_total', 0)  # 기존 투표 카운트의 합을 가져오거나 0으로 초기화

                # 투표 당한 사람 이름을 기록 (vote는 투표 당한 사람의 이름)
                if vote not in vote_count:
                    vote_count[vote] = 0  # 처음 투표 받은 사람이라면 카운트 0으로 초기화

                vote_count[vote] += 1  # 투표 받은 사람의 카운트를 1 증가시킴
                count += 1  # 투표할 때마다 count 증가
                room['vote_count_total'] = count  # 전체 투표 수 업데이트
                # 투표 결과 출력
                print(f"Room ID: {room_id}, Vote: {vote}, Vote Count: {vote_count[vote]}")
                # 클라이언트 이름 가져오기
                name = self.clients.get(client, "Unknown Player")
                self.broadcast(f"{name}님은 {vote}님을 라이어로 지목하였습니다.", room_id)
                # 방에 투표 카운트를 저장
                room['vote_count'] = vote_count

                if room['vote_count_total'] == len(room['players']):  # 모든 플레이어가 투표를 마친 경우
                    # 투표수가 가장 많은 사람 이름 찾기
                    most_voted_player = max(vote_count, key=vote_count.get)
                    self.process_vote(room_id, most_voted_player)

            elif message.startswith("ANSWER"):
                _, room_id, answer = message.split(' ', 2)
                room_id = room_id

                print(f"Room ID: {room_id}, Message: {answer}")
                print(f"Room ID: {room_id}, Player's Answer: {answer}")

                # 실제 정답 가져오기
                room = self.rooms[room_id]
                correct_answer = room['answer']
                liar = room['liar']
                liar_name = self.clients[liar]  # 라이어의 이름 가져오기

                # 정답 비교
                if answer == correct_answer:
                    self.broadcast(f"플레이어 {liar_name}는 답변 '{answer}'로 정답을 맞췄습니다! 라이어가 승리합니다!\n", room_id)
                else:
                    self.broadcast(f"플레이어 {liar_name}는 답변 '{answer}'로 정답을 맞추지 못했습니다! 라이어가 패배합니다!\n", room_id)

                # 게임 종료 메시지
                self.broadcast("게임이 종료되었습니다.\n", room_id)
                time.sleep(3)  # 3초 대기
                self.end_game(room_id)  # 게임 종료 처리 함수 호출

            if message.startswith("EXIT_ROOM"):
                _, room_id = message.split(' ', 1)  # room_id 추출
                room_id = room_id  # room_id를 정수로 변환
                # 해당 방 정보를 가져옵니다
                room = self.rooms[room_id]
                name = self.clients.get(client, "Unknown Player")
                if room:
                    # 방에 있는 플레이어 목록에서 해당 클라이언트 삭제
                    if client in room['players']:
                        room['players'].remove(client)  # 클라이언트 소켓을 방에서 제거
                        print(f"클라이언트가 {room_id}번 방에서 퇴장했습니다.")

                        # 방에 플레이어가 더 이상 없으면 방을 삭제 (필요 시)
                        if not room['players']:
                            del self.rooms[room_id]  # 방을 삭제하는 조건 추가 가능
                            print(f"방 {room_id}가 더 이상 플레이어가 없으므로 삭제되었습니다.")

                        # 퇴장한 클라이언트에게 퇴장 메시지 전송
                        self.send_to_client(client, f"{room_id}번 방에서 나가셨습니다.\n")

                        # 방에 남아있는 플레이어들에게 퇴장 사실 알리기
                        self.broadcast(f"{name}님이 방에서 퇴장했습니다.\n", room_id)
                    else:
                        print(f"클라이언트 {client}는 {room_id}번 방에 없습니다.")
                else:
                    print(f"해당 방 {room_id}가 존재하지 않습니다.")


    def process_vote(self, room_id, most_voted_player):
        room = self.rooms[room_id]
        # 라이어의 소켓 객체를 가져와서 해당하는 이름을 찾기
        liar_socket = room['liar']  # room['liar']에 저장된 소켓 객체
        # 소켓 객체에서 이름을 찾기
        liar_name = self.clients.get(liar_socket, "Unknown Player")  # 'Unknown Player'는 이름을 못 찾았을 때 기본값
        print("투표 짱 : " + most_voted_player)
        print("라이어 : " + liar_name)

        # 가장 많은 표를 받은 사람과 라이어를 비교
        if most_voted_player == liar_name:
            self.broadcast(f"라이어를 맞췄습니다! 플레이어 {most_voted_player}가 라이어였습니다.\n", room_id)
            self.send_to_client(liar_socket, "라이어는 정답을 맞춰주세요.\n")

        else:
            self.broadcast(f"라이어가 아닙니다! 플레이어 {most_voted_player}는 라이어가 아닙니다.\n", room_id)
            self.broadcast(f"라이어는 {liar_name}님이었습니다.\n", room_id)
            self.broadcast(f"라이어의 승리!!\n", room_id)

    def start_game_in_room(self, room_id):
        room = self.rooms[room_id]
        players = room['players']
        liar = random.choice(players)
        topic = random.choice(list(self.answers.keys()))
        answer = random.choice(self.answers[topic])

        # 설명 순서 생성
        room['explanation_order'] = random.sample(players, len(players))
        room['current_turn'] = 0
        room['topic'] = topic
        room['answer'] = answer
        room['liar'] = liar
        count = 0
        for player in players:
            if player == liar:
                self.send_to_client(player, f"당신은 라이어입니다! 주제는 '{topic}'입니다.\n")
                count += 1
            else:
                self.send_to_client(player, f"주제는 '{topic}'입니다. 답변은 '{answer}'입니다.\n")
                count += 1
        print(count)

        self.broadcast("게임이 시작되었습니다! 설명 차례가 시작됩니다.\n", room_id)
        self.notify_turn(room_id)

    def notify_turn(self, room_id):
        room = self.rooms[room_id]
        current_turn = room['current_turn']
        current_player = room['explanation_order'][current_turn]

        for player in room['players']:
            if player == current_player:
                self.send_to_client(player, "당신의 차례입니다. 답변을 설명하세요.\n")
            else:
                self.send_to_client(player, f"다른 플레이어가 설명 중입니다.\n")

    def handle_explanation(self, client, room_id, ex):
        room = self.rooms[room_id]
        current_turn = room['current_turn']
        current_player = room['explanation_order'][current_turn]

        if client == current_player:
            if ex:
                player_name = self.clients.get(current_player, "Unknown Player")  # 이름 가져오기
                self.broadcast(f"플레이어 {player_name}의 설명: {ex}\n", room_id)
                room['current_turn'] += 1  # 차례 진행

                # 다음 차례로 넘어가는지 체크
                if room['current_turn'] < len(room['explanation_order']):
                    self.notify_turn(room_id)
                else:
                    self.broadcast("설명이 끝났습니다. 투표를 시작합니다!\n", room_id)



    def start_game(self):
        while True:
            client, addr = self.server_socket.accept()
            Thread(target=self.handle_client, args=(client, addr)).start()

    def end_game(self, room_id):
        if room_id in self.rooms:
            self.broadcast("게임이 종료되었습니다. 메인 화면으로 이동합니다.\n", room_id)  # 모든 클라이언트에게 메시지 전송
            self.broadcast("EXIT_TO_MAIN", room_id)  # 클라이언트들에게 메인 화면 이동 명령 전송
            self.rooms.pop(room_id)  # 해당 방 정보 삭제
        print(f"Room {room_id} has been cleared and the game has ended.")


if __name__ == "__main__":
    server = LiarGameServer()