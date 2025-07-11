import random
import queue
from termcolor import cprint
import emoji

def load_words_from_txt(file_path):
    all_words = []
    word_list = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:  # 结束
                if word_list:
                    all_words.append(word_list)
                    word_list = []
            # 根据最后一个空格切分（防止释义中也有空格）
            if ' ' in line:
                idx = line.rfind(' ')
                word = line[:idx].strip()
                meaning = line[idx+1:].strip()
                word_list.append((word, meaning))
    if word_list:  # 添加最后一组单词
        all_words.append(word_list)
    return all_words

def run_flashcards(word_list,forget_queue):

    # shuffle all the words
    if_shuffle = input(f"Load {len(word_list)} words form this part. If you want to shuffle all the words loaded?(y/n)")
    if if_shuffle == 'y' or "yes" in if_shuffle.lower():
        random.shuffle(word_list)
    

    if forget_queue is not None:
        print("You have a queue for forgetting words.")
        cprint("按下 ENTER 查看释义，输入 q 回车可随时退出。如果忘记了输入 '4' ,'3' 或 'p' ，然后 ENTER!\n","green")

        for word, meaning in word_list:
            forget_queue.put((word, meaning))

        while not forget_queue.empty():
            word, meaning = forget_queue.get()
            user_input = input(f"英文：{word}")
            if user_input.strip().lower() == 'q':
                print("已退出。")
                return forget_queue
            elif user_input.strip() == '4' or user_input.strip() == '3' or user_input.strip().lower() == 'p':
                forget_queue.put((word, meaning))
                cprint(f"释义：{meaning}, add to the queue.\n","green")
                continue
            else:
                print(f"释义：{meaning}\n")
    else:
        cprint("按下 ENTER 查看释义，输入 q 回车可随时退出\n","green")
        for word, meaning in word_list:
            user_input = input(f"英文：{word}")
            if user_input.strip().lower() == 'q':
                print("已退出。")
                break
            print(f"释义：{meaning}\n")



if __name__ == "__main__":


    cprint(emoji.emojize("🚀 Welcome to the Flashcard Learning System! 🚀", language='alias'),
       'green', 'on_black', attrs=['bold'])

    cprint(emoji.emojize("📚 This system is designed to help you learn vocabulary efficiently. 📚", language='alias'),
       'green', 'on_black', attrs=['bold'])

    file_path = "2.txt"  # 替换为你的文件路径
    all_words = load_words_from_txt(file_path)

    print(f"Having load {len(all_words)} parts of words from {file_path}.")
    part_idx = input(f"Which part do you want to learn? (1-{len(all_words)})")

    if not part_idx.isdigit() or int(part_idx) < 1 or int(part_idx) > len(all_words):
        print(f"Invalid part index. Please enter a number between 1 and {len(all_words)}.")
        exit(1)

    words = all_words[int(part_idx)-1]



    if_queue = input("Do you want to use a queue for forgetting words? (y/n): ")
    

    if not words:
        print("Error: No words found in this part.")
    elif if_queue.lower() == 'y' or if_queue.lower() == 'yes':
        cprint("You have a queue for forgetting words.",'blue')
        forget_queue = queue.Queue()
        forget_queue = run_flashcards(words,forget_queue)
    else:
        run_flashcards(words, None)



message = emoji.emojize("🎉 Congratulations! You have finished this part. 🎉", language='alias')
cprint(message, 'green', 'on_yellow', attrs=['bold'])
