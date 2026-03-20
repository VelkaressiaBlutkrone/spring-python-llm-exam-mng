package com.sample.llm._core.utils;

import lombok.AllArgsConstructor;
import lombok.Getter;
import org.springframework.http.HttpStatus;

@Getter
@AllArgsConstructor
public class Resp<T> {

    private int status;
    private String msg;
    private T body;

    public static <T> Resp<T> ok(T body) {
        return new Resp<>(200, "성공", body);
    }

    public static Resp<?> fail(HttpStatus status, String msg) {
        return new Resp<>(status.value(), msg, null);
    }
}
