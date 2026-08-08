package com.kidgames.mathquest.screen;

import com.kidgames.mathquest.network.QuestInvitationResponsePayload;

final class QuestInvitationResponseFlow {
    @FunctionalInterface
    interface Closer {
        void close();
    }

    @FunctionalInterface
    interface ResponseSender {
        void send(QuestInvitationResponsePayload payload);
    }

    private QuestInvitationResponseFlow() {}

    static void respond(boolean accepted, Closer closer, Runnable acceptedAction, ResponseSender responseSender) {
        if (closer != null) {
            closer.close();
        }
        if (accepted && acceptedAction != null) {
            acceptedAction.run();
        }
        if (responseSender != null) {
            responseSender.send(new QuestInvitationResponsePayload(accepted));
        }
    }
}
