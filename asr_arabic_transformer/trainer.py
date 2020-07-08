import copy
import torch
from os import path
from asr_arabic_transformer.utils import shuffle_jointly


class Trainer:
    def __init__(self, X_train, X_valid, y_train, y_valid, get_batch, model, optimizer, loss_function, seed=636248):
        self.X_train = X_train
        self.X_valid = X_valid
        self.y_train = y_train
        self.y_valid = y_valid
        self.model = model
        self.num_exec = 0
        self.get_batch = get_batch
        self.seed = seed
        self.optimizer = optimizer
        self.loss_function = loss_function
        self.best_model = None

    def train(self, print_every, batch_size, max_epochs, early_stop_epochs, path_save="", save_name="model_save{}.pt"):
        self.num_exec += 1
        train_loss_history = []
        valid_loss_history = []
        best_loss = float("inf")
        self.best_model = None
        epochs_without_improving = 0
        X_train = self.X_train
        X_valid = self.X_valid
        y_train = self.y_train
        y_valid = self.y_valid

        for i in range(max_epochs):
            X_train, y_train = shuffle_jointly(X_train, y_train)
            train_gen = self.get_batch(X_train, y_train, batch_size)
            valid_gen = self.get_batch(X_valid, y_valid, batch_size)
            print("Epoch", i)
            loss = 0
            count = 0
            self.model.train()
            for x, target in train_gen:
                loss += self.model.fit_batch(x, target)
                train_loss_history.append(loss)
                count += 1
                if count % print_every == 0:
                    print("Iteration :", len(train_loss_history), "Loss :", loss / count)

            valid_loss = 0
            loss /= count
            count = 0
            self.model.eval()
            for x, target in valid_gen:
                valid_loss += self.model.eval_batch(x, target)
                valid_loss_history += [valid_loss] * (len(valid_loss_history) - len(train_loss_history))
                count += 1
            valid_loss /= count
            print("Training Loss   :", loss)
            print("Validation Loss :", valid_loss)

            if valid_loss < best_loss:
                print("New best reached!   Saving Model...")
                best_loss = valid_loss
                self.best_model = copy.deepcopy(self.model)
                infos = {"valid_loss": valid_loss, "train_loss": loss,
                         "train_loss_history": train_loss_history,
                         "valid_loss_history": valid_loss_history,
                         "state_dict": self.best_model.state_dict()}
                torch.save(infos, path.join(path_save, save_name.format(1)))

                epochs_without_improving = 0
            else:
                epochs_without_improving += 1
            if early_stop_epochs < epochs_without_improving:
                break
            print("\n\n")
        print("Best Validation Loss : ", best_loss)

    def fit_batch(self, x, target):
        self.optimizer.zero_grad()
        out = self.model(x, target[:,:-1])
        loss = self.loss_function(out[:,:target.size(1)-1,:], target[:,1:,:])
        loss.backward()
        self.optimizer.step()
        return loss.item()

    def eval_batch(self, x, target):
        out = self.model(x, target[:,:-1])
        loss = self.loss_function(out[:,:target.size(1)-1,:], target[:,1:,:])
        return loss.item()
